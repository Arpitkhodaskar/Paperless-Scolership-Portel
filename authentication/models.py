from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """Extended User model with additional fields"""
    
    USER_TYPES = (
        ('student', 'Student'),
        ('institute_admin', 'Institute Admin'),
        ('department_admin', 'Department Admin'),
        ('finance_admin', 'Finance Admin'),
        ('grievance_admin', 'Grievance Admin'),
        ('super_admin', 'Super Admin'),
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    class Meta:
        db_table = 'auth_users'


class UserProfile(models.Model):
    """Additional profile information for users"""
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"
    
    class Meta:
        db_table = 'user_profiles'
