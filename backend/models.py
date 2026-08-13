from django.db import models

# Create your models here.
class Profile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    longitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    phone_number = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.user.username