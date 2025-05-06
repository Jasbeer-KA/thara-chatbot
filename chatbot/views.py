from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from .logic.chatbot_engine import ChatbotEngine
import os
from django.conf import settings
import logging
import uuid
import json
from django.utils.text import get_valid_filename
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)
bot = ChatbotEngine()

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_CONTENT_TYPES = [
    'application/pdf', 
    'text/plain',
    'image/jpeg', 
    'image/png', 
    'image/gif', 
    'image/bmp'
]

def home(request):
    return render(request, "base.html")

def validate_response(response):
    """Ensure response is in a valid format for AIMessage"""
    if response is None:
        return "No response generated"
    if isinstance(response, (str, list)):
        return response
    return str(response)

@csrf_exempt
def chat_view(request):
    if request.method == "POST":
        try:
            # Initialize variables
            question = ""
            document = None
            response = ""
            
            # Handle different content types
            if request.content_type == 'application/json':
                try:
                    data = json.loads(request.body)
                    question = data.get("question", "").strip()
                except json.JSONDecodeError:
                    return JsonResponse({"error": "Invalid JSON format"}, status=400)
            else:
                question = request.POST.get("question", "").strip()
                document = request.FILES.get("document")

            # Process document if uploaded
            if document:
                # Validate file
                if document.size > MAX_FILE_SIZE:
                    return JsonResponse({"error": "File size exceeds 5MB limit."}, status=400)
                if document.content_type not in ALLOWED_CONTENT_TYPES:
                    return JsonResponse({"error": "Unsupported file type."}, status=400)

                # Save file temporarily
                safe_filename = get_valid_filename(f"{uuid.uuid4()}_{document.name}")
                file_path = default_storage.save(f"uploads/{safe_filename}", document)
                absolute_file_path = default_storage.path(file_path)

                try:
                    if document.content_type.startswith('image/'):
                        response = bot.process_image(absolute_file_path)
                    else:
                        doc_content = bot.process_document(absolute_file_path)
                        enhanced_question = (
                            f"{question}\n\nDocument content:\n{doc_content}" 
                            if question else 
                            f"Please analyze this document:\n{doc_content}"
                        )
                        response = bot.general_query(enhanced_question)
                except Exception as e:
                    logger.error(f"File processing error: {str(e)}", exc_info=True)
                    response = f"Error processing file: {str(e)}"
                finally:
                    if default_storage.exists(file_path):
                        default_storage.delete(file_path)

            # Process text question if no document
            elif question:
                try:
                    response = bot.general_query(question)
                except Exception as e:
                    logger.error(f"Query processing error: {str(e)}", exc_info=True)
                    response = "Sorry, an error occurred while processing your question."

            # Validate and store conversation
            if question or document:
                try:
                    # Ensure response is in valid format
                    valid_response = validate_response(response)
                    user_input = question or document.name
                    
                    # Ensure user_input is not empty
                    if not user_input.strip():
                        user_input = "File upload" if document else "Empty query"
                        
                    bot._store_conversation(user_input, valid_response)
                except Exception as e:
                    logger.error(f"History save error: {str(e)}", exc_info=True)

            # Return appropriate response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    "response": response,
                    "status": "success"
                })
            
            return render(request, 'base.html', {
                "response": response,
                "question": question
            })

        except Exception as e:
            logger.error(f"Chat view error: {str(e)}", exc_info=True)
            return JsonResponse({
                "error": "An unexpected error occurred",
                "details": str(e)
            }, status=500)

    # GET request - render template with history
    try:
        history = []
        bot.cursor.execute(
            "SELECT user_query, bot_response FROM chat_history ORDER BY timestamp DESC LIMIT 10"
        )
        history = bot.cursor.fetchall()
    except Exception as e:
        logger.error(f"History fetch error: {str(e)}")
        history = []

    return render(request, 'base.html', {
        'history': history,
        'response': request.GET.get('response', ''),
        'question': request.GET.get('question', '')
    })

class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            file = request.data.get("document")
            if not file:
                return Response({"error": "No file provided"}, status=400)

            # Validate file
            if file.size > MAX_FILE_SIZE:
                return Response({"error": "File too large"}, status=400)
            if file.content_type not in ALLOWED_CONTENT_TYPES:
                return Response({"error": "Unsupported file type"}, status=400)

            # Save temporarily
            file_path = os.path.join(settings.MEDIA_ROOT, file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            try:
                if file.content_type.startswith('image/'):
                    result = bot.process_image(file_path)
                else:
                    result = bot.process_document(file_path)
                
                return Response({
                    "result": result,
                    "status": "success"
                })
            except Exception as e:
                logger.error(f"Document processing error: {str(e)}", exc_info=True)
                return Response({
                    "error": str(e),
                    "status": "error"
                }, status=500)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
        except Exception as e:
            logger.error(f"Document upload error: {str(e)}", exc_info=True)
            return Response({
                "error": str(e),
                "status": "error"
            }, status=500)

@api_view(['POST'])
def debug_upload(request):
    """Endpoint for testing file uploads"""
    file = request.FILES.get('document')
    if file:
        return Response({
            'name': file.name,
            'size': file.size,
            'content_type': file.content_type,
            'received': True,
            'status': 'success'
        })
    
    return Response({
        'error': 'No file received',
        'status': 'error'
    }, status=400)