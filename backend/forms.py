from django import forms
from django.contrib.auth.models import User
from .models import Profile, KYC, ServiceRequest, ServiceCategory


class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'First Name',
            'id': 'id_first_name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'Last Name',
            'id': 'id_last_name'
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'name@example.com',
            'id': 'id_email'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'Username',
            'id': 'id_username'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']


class ProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input-hidden',
            'id': 'id_profile_picture',
            'accept': 'image/*'
        })
    )

    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control-textarea',
            'placeholder': 'Write a short bio about yourself, your skills, or professional experience...',
            'rows': 4,
            'id': 'id_bio'
        })
    )

    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. 9800000000',
            'id': 'id_phone_number'
        })
    )

    skills = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. Electrical, HVAC, Plumbing, Auto Repair',
            'id': 'id_skills'
        })
    )

    hourly_rate = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'Rate per hour ($ or NPR)',
            'id': 'id_hourly_rate'
        })
    )

    latitude = forms.DecimalField(
        max_digits=15,
        decimal_places=12,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. 27.717245300000',
            'step': 'any',
            'id': 'id_latitude'
        })
    )

    longitude = forms.DecimalField(
        max_digits=15,
        decimal_places=12,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. 85.323960500000',
            'step': 'any',
            'id': 'id_longitude'
        })
    )

    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control-select',
            'id': 'id_role'
        })
    )

    availability_status = forms.ChoiceField(
        choices=Profile.AVAILABILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control-select',
            'id': 'id_availability_status'
        })
    )

    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-toggle-checkbox',
            'id': 'id_is_active'
        })
    )

    is_deleted = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-toggle-checkbox',
            'id': 'id_is_deleted'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'profile_picture',
            'bio',
            'phone_number',
            'role',
            'skills',
            'hourly_rate',
            'availability_status',
            'latitude',
            'longitude',
            'is_active',
            'is_deleted',
        ]


class KYCForm(forms.ModelForm):
    citizenship_number = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. 27-01-79-04512 or ID number',
            'id': 'id_citizenship_number'
        })
    )

    citizenship_front_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input-hidden',
            'id': 'id_citizenship_front_image',
            'accept': 'image/*'
        })
    )

    citizenship_back_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input-hidden',
            'id': 'id_citizenship_back_image',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = KYC
        fields = [
            'citizenship_number',
            'citizenship_front_image',
            'citizenship_back_image',
        ]


class ServiceRequestForm(forms.ModelForm):
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. AC Repair & Gas Refill',
            'id': 'id_req_title'
        })
    )

    service_type = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. Emergency Electrical Fix',
            'id': 'id_req_service_type'
        })
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control-textarea',
            'placeholder': 'Describe what needs fixing or the service requirement in detail...',
            'rows': 4,
            'id': 'id_req_description'
        })
    )

    priority = forms.ChoiceField(
        choices=ServiceRequest.PRIORITY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control-select',
            'id': 'id_req_priority'
        })
    )

    customer_address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'Street Address, City or Area',
            'id': 'id_req_address'
        })
    )

    customer_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'Contact phone number for technician',
            'id': 'id_req_phone'
        })
    )

    price_estimate = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'Offer / Estimated Budget ($ or NPR)',
            'id': 'id_req_price_estimate'
        })
    )

    class Meta:
        model = ServiceRequest
        fields = [
            'category',
            'title',
            'service_type',
            'description',
            'priority',
            'customer_address',
            'customer_phone',
            'customer_latitude',
            'customer_longitude',
            'price_estimate',
        ]
