from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, blank=False, null=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, blank=True, null=True)  # Campo para el nombre
    last_name = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    belt_rank = models.CharField(max_length=50)  
    dojo = models.CharField(max_length=100) 
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    age = models.IntegerField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True, null=True)
    enrollment_date = models.DateField(auto_now_add=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    neighborhood = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    social_media_links = models.JSONField(blank=True, null=True)
    
    def __str__(self):
        return self.user.username