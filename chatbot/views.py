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
            # Process the document
            file_path = os.path.join(settings.BASE_DIR, 'media', document.name)
            
            try:
                # Save the file temporarily
                with open(file_path, 'wb+') as destination:
                    for chunk in document.chunks():
                        destination.write(chunk)
                
                # Get file info for debugging
                file_info = {
                    'name': document.name,
                    'size': document.size,
                    'content_type': document.content_type
                }
                logger.info(f"Processing file: {file_info}")
                
                # Process document based on type
                content_type = document.content_type.lower()
                if (document.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) or 
                    content_type.startswith('image/')):
                    # For images
                    logger.info("Processing as image")
                    response = bot.process_image(file_path)
                else:
                    # For documents
                    logger.info("Processing as document")
                    document_content = bot.process_document(file_path)
                    
                    if question:
                        enhanced_question = f"{question}\n\nDocument content:\n{document_content}"
                    else:
                        enhanced_question = f"Please analyze this document:\n{document_content}"
                    
                    response = bot.general_query(enhanced_question)
                
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                response = f"Error processing file: {str(e)}"
                
            finally:
                # Clean up the temporary file
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as e:
                    logger.error(f"Error removing temp file: {str(e)}")
        else:
            if question:  # Only process if there's actually a question
                response = bot.general_query(question)
        
        # Save to chat history if we have content
        if question or document:
            try:
                bot.cursor.execute(
                    "INSERT INTO chat_history (user_query, bot_response) VALUES (?, ?)",
                    (question, response)
                )
                bot.conn.commit()
            except Exception as e:
                logger.error(f"Error saving to chat history: {str(e)}")
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"response": response})
        return render(request, 'base.html', {"response": response})
    
    return render(request, 'base.html')

class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.data.get("document")
        if not file:
            return Response({"error": "No file provided"}, status=400)

        file_path = os.path.join(settings.BASE_DIR, 'media', file.name)
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            content_type = file.content_type.lower()
            if (file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) or content_type.startswith('image/')):
                result = bot.process_image(file_path)
            else:
                result = bot.process_document(file_path)
            
            return Response({"result": result}, content_type="application/json")
        except Exception as e:
            logger.error(f"Error in DocumentUploadView: {str(e)}", exc_info=True)
            return Response({"error": str(e)}, status=500)
        finally:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing temp file: {str(e)}")

@api_view(['POST'])
def debug_upload(request):
    """Endpoint for testing file uploads"""
    file = request.FILES.get('document')
    if file:
        return Response({
            'name': file.name,
            'size': file.size,
            'content_type': file.content_type,
            'received': True
        })
    return Response({'error': 'No file received'}, status=400)

