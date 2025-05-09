from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    phone = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.username


class ChatHistory(models.Model):
    user_query = models.TextField()
    bot_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.user_query[:50]}..."


class Document(models.Model):
    filename = models.CharField(max_length=255)
    content = models.TextField()
    embedding_id = models.CharField(max_length=255, unique=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
