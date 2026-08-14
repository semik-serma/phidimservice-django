from django import forms
from django.contrib.auth.models import User
from .models import Profile, KYC

class UserUpdateForm(forms.ModelForm):
    """
    Form for updating basic auth.User information.
    """
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
    """
    Form for updating Profile model fields with purpose-driven sectioning.
    """
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
            'placeholder': 'Write a short bio about yourself, your interests, or professional background...',
            'rows': 4,
            'id': 'id_bio'
        })
    )

    phone_number = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': '9800000000',
            'maxlength': '10',
            'id': 'id_phone_number'
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
            'latitude',
            'longitude',
            'is_active',
            'is_deleted',
        ]

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '')
        if phone:
            phone = phone.strip()
            if not phone.isdigit():
                raise forms.ValidationError("Phone number must contain digits only.")
            if len(phone) != 10:
                raise forms.ValidationError("Phone number must be exactly 10 digits.")
        return phone


class KYCForm(forms.ModelForm):
    """
    Form for uploading and updating KYC (Know Your Customer) documents and citizenship ID.
    """
    citizenship_number = forms.CharField(
        max_length=17,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control-input',
            'placeholder': 'e.g. 27-01-79-04512 or ID number',
            'maxlength': '17',
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

    def clean_citizenship_number(self):
        c_num = self.cleaned_data.get('citizenship_number', '')
        if c_num:
            c_num = c_num.strip()
            if len(c_num) > 17:
                raise forms.ValidationError("Citizenship number cannot exceed 17 characters.")
        return c_num
