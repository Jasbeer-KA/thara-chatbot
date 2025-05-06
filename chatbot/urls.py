# chat/urls.py
from django.urls import path
from .views import DocumentUploadView,home
from .import views

urlpatterns = [
    path("", home, name="home"),
    path("api/upload/", DocumentUploadView.as_view(), name="upload_api"),
    path("chat/", views.chat_view, name="chat"),  # URL for chat view

]