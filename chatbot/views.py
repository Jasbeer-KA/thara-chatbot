from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from .logic.chatbot_engine import ChatbotEngine
import os
from django.conf import settings
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize the chatbot engine once when the module loads
bot = ChatbotEngine()

# Ensure media directory exists
os.makedirs(os.path.join(settings.BASE_DIR, 'media'), exist_ok=True)

def home(request):
    return render(request, 'base.html')

def chat_view(request):
    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        document = request.FILES.get("document")
        
        response = ""
        
        if document:
            # Log file information before processing
            file_info = {
                'name': document.name,
                'size': document.size,
                'content_type': document.content_type,
                'user': request.user.username if request.user.is_authenticated else 'anonymous'
            }
            logger.info(f"File upload initiated: {file_info}")
            
            # Process the document
            file_path = os.path.join(settings.BASE_DIR, 'media', document.name)
            
            try:
                # Save the file temporarily
                with open(file_path, 'wb+') as destination:
                    for chunk in document.chunks():
                        destination.write(chunk)
                
                logger.info(f"File saved temporarily at: {file_path}")
                
                # Process document based on type
                content_type = document.content_type.lower()
                if (document.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) or 
                    content_type.startswith('image/')):
                    logger.info("Processing as image file")
                    response = bot.process_image(file_path)
                else:
                    logger.info("Processing as document file")
                    document_content = bot.process_document(file_path)
                    
                    if question:
                        enhanced_question = f"{question}\n\nDocument content:\n{document_content}"
                        logger.debug(f"Enhanced question with document content")
                    else:
                        enhanced_question = f"Please analyze this document:\n{document_content}"
                    
                    response = bot.general_query(enhanced_question)
                
                logger.info(f"Successfully processed file: {document.name}")
                
            except Exception as e:
                logger.error(f"Error processing file {document.name}: {str(e)}", exc_info=True)
                response = f"Error processing file: {str(e)}"
                
            finally:
                # Clean up the temporary file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.debug(f"Temporary file {file_path} removed")
                except Exception as e:
                    logger.error(f"Error removing temp file {file_path}: {str(e)}")
        else:
            if question:  # Only process if there's actually a question
                logger.info(f"Processing text query: {question[:100]}...")  # Log first 100 chars
                response = bot.general_query(question)
        
        # Save to chat history if we have content
        if question or document:
            try:
                bot.cursor.execute(
                    "INSERT INTO chat_history (user_query, bot_response) VALUES (?, ?)",
                    (question, response)
                )
                bot.conn.commit()
                logger.debug("Chat history updated successfully")
            except Exception as e:
                logger.error(f"Error saving to chat history: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            logger.debug("Returning JSON response")
            return JsonResponse({"response": response})
        
        logger.debug("Rendering template response")
        return render(request, 'base.html', {"response": response})
    
    logger.debug("Rendering empty chat template")
    return render(request, 'base.html')

class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.data.get("document")
        if not file:
            logger.warning("No file provided in DocumentUploadView")
            return Response({"error": "No file provided"}, status=400)

        # Log file information
        file_info = {
            'name': file.name,
            'size': file.size,
            'content_type': file.content_type,
            'user': request.user.username if request.user.is_authenticated else 'anonymous'
        }
        logger.info(f"API file upload initiated: {file_info}")

        file_path = os.path.join(settings.BASE_DIR, 'media', file.name)
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            logger.info(f"File saved temporarily at: {file_path}")

            content_type = file.content_type.lower()
            if (file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) or content_type.startswith('image/')):
                logger.info("Processing as image file via API")
                result = bot.process_image(file_path)
            else:
                logger.info("Processing as document file via API")
                result = bot.process_document(file_path)
            
            logger.info(f"Successfully processed file via API: {file.name}")
            return Response({"result": result}, content_type="application/json")
            
        except Exception as e:
            logger.error(f"API Error processing file {file.name}: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)
            
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Temporary API file {file_path} removed")
            except Exception as e:
                logger.error(f"Error removing temp API file {file_path}: {str(e)}")

@api_view(['POST'])
def debug_upload(request):
    """Endpoint for testing file uploads"""
    file = request.FILES.get('document')
    if file:
        file_info = {
            'name': file.name,
            'size': file.size,
            'content_type': file.content_type,
            'user': request.user.username if request.user.is_authenticated else 'anonymous'
        }
        logger.info(f"Debug upload received: {file_info}")
        return Response({
            'name': file.name,
            'size': file.size,
            'content_type': file.content_type,
            'received': True
        })
    
    logger.warning("Debug upload endpoint called with no file")
    return Response({'error': 'No file received'}, status=400)