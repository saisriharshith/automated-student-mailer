from django.db import models
from django.contrib.auth.models import User

class UploadFile(models.Model):
    file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload at {self.uploaded_at}"

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    app_password = models.CharField(max_length=100)

    def __str__(self):
        return self.user.email