from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    ROLE_CHOICES = [
        ('customer', 'Customer / User'),
        ('technician', 'Technician / Specialist'),
        ('admin', 'Administrator'),
    ]

    AVAILABILITY_CHOICES = [
        ('available', 'Available for Jobs'),
        ('busy', 'Currently on Job'),
        ('offline', 'Offline'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    bio = models.TextField(blank=True)
    
    # Location and Telemetry
    latitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    longitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True, help_text="Accuracy in meters")
    location_updated_at = models.DateTimeField(null=True, blank=True)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Contact & Verification
    phone_number = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)

    # Technician specific fields
    skills = models.CharField(max_length=255, blank=True, help_text="Comma-separated skills (e.g. Electrical, Plumbing, HVAC)")
    experience_years = models.PositiveIntegerField(default=1)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_reviews = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def full_name(self):
        name = f"{self.user.first_name} {self.user.last_name}".strip()
        return name if name else self.user.username

    @property
    def display_avatar(self):
        if self.profile_picture:
            return self.profile_picture.url
        return "/static/images/customer-avatars.png"


class KYC(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='kyc')
    citizenship_number = models.CharField(max_length=30)
    citizenship_front_image = models.ImageField(upload_to='kyc_documents/', null=True, blank=True)
    citizenship_back_image = models.ImageField(upload_to='kyc_documents/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return f"KYC for {self.profile.user.username} [{self.get_status_display()}]"


class ServiceCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon_class = models.CharField(max_length=50, default='fa-solid fa-wrench')
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=8, decimal_places=2, default=500.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Finding Technician'),
        ('ACCEPTED', 'Technician Assigned'),
        ('EN_ROUTE', 'Technician En Route'),
        ('IN_PROGRESS', 'Service In Progress'),
        ('COMPLETED', 'Service Completed'),
        ('CANCELLED', 'Request Cancelled'),
    ]

    PRIORITY_CHOICES = [
        ('standard', 'Standard (Same Day / Regular)'),
        ('urgent', 'Urgent Emergency (Priority)'),
        ('scheduled', 'Scheduled Appointment'),
    ]

    # Parties
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_requests')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='technician_jobs')
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='requests')

    # Job Details
    title = models.CharField(max_length=200)
    service_type = models.CharField(max_length=100, default='General Diagnostics & Repair')
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='standard')

    # Customer Location at time of request
    customer_latitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    customer_longitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    customer_address = models.CharField(max_length=255, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)

    # Live Technician Telemetry for this active job
    technician_latitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    technician_longitude = models.DecimalField(max_digits=15, decimal_places=12, null=True, blank=True)
    technician_location_updated_at = models.DateTimeField(null=True, blank=True)

    # Commercials
    price_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Schedule & Timestamps
    scheduled_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"REQ-{self.id}: {self.title} ({self.get_status_display()})"

    @property
    def is_active_job(self):
        return self.status in ['ACCEPTED', 'EN_ROUTE', 'IN_PROGRESS']


class CallSession(models.Model):
    STATUS_CHOICES = [
        ('initiated', 'Initiated / Ringing'),
        ('connected', 'Connected in Call'),
        ('ended', 'Completed / Ended'),
        ('rejected', 'Call Rejected'),
        ('missed', 'Missed Call'),
    ]

    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='call_sessions')
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_calls')
    room_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    started_at = models.DateTimeField(auto_now_add=True)
    connected_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Call {self.room_id} [{self.caller.username} -> {self.receiver.username}] ({self.status})"


class ChatMessage(models.Model):
    request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg from {self.sender.username} on REQ-{self.request_id}"