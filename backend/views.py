from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Profile, KYC
from .forms import ProfileForm, UserUpdateForm, KYCForm

def home(request):
    return render(request, 'home/index.html')

def about(request):
    return render(request, 'home/about.html')

def services(request):
    return render(request, 'home/services.html')

def contact(request):
    return render(request, 'home/about.html')

def product_detail(request, product_id='aeroflow-max'):
    context = {
        'product_id': product_id,
        'title': 'AEROFLOW MAX',
        'subtitle': 'Active Noise Canceling Headphones',
        'rating': '4.8',
        'reviews_count': '1,450',
        'original_price': '399',
        'price': '299.00',
        'savings': '100',
        'description': 'Immerse yourself in pure sound. Experience industry-leading Active Noise Cancellation, 40-hour battery life, and unparalleled comfort.'
    }
    return render(request, 'home/product_detail.html', context)

def profile(request):
    """
    Profile management view displaying editable fields partitioned by purpose.
    Supports authenticated editing, KYC document upload, and graceful preview.
    """
    if request.user.is_authenticated:
        user_profile, created = Profile.objects.get_or_create(user=request.user)
        try:
            kyc_instance = user_profile.kyc
        except (KYC.DoesNotExist, AttributeError):
            kyc_instance = None
        
        if request.method == 'POST':
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileForm(request.POST, request.FILES, instance=user_profile)
            k_form = KYCForm(request.POST, request.FILES, instance=kyc_instance)
            
            if u_form.is_valid() and p_form.is_valid() and k_form.is_valid():
                u_form.save()
                p_form.save()

                c_num = k_form.cleaned_data.get('citizenship_number')
                front_img = k_form.cleaned_data.get('citizenship_front_image')
                back_img = k_form.cleaned_data.get('citizenship_back_image')

                if kyc_instance:
                    k_form.save()
                elif c_num or front_img or back_img:
                    kyc_obj = k_form.save(commit=False)
                    kyc_obj.profile = user_profile
                    kyc_obj.save()

                if k_form.has_changed():
                    user_profile.is_verified = False
                    user_profile.save()

                messages.success(request, 'Profile and KYC documents successfully updated!')
                return redirect('profile')
            else:
                messages.error(request, 'Please check the form for errors and try again.')
        else:
            u_form = UserUpdateForm(instance=request.user)
            p_form = ProfileForm(instance=user_profile)
            k_form = KYCForm(instance=kyc_instance)
            
        context = {
            'u_form': u_form,
            'p_form': p_form,
            'k_form': k_form,
            'profile': user_profile,
            'kyc': kyc_instance,
            'is_demo': False
        }
    else:
        # Fallback / Preview state for unauthenticated viewers
        if request.method == 'POST':
            messages.warning(request, 'Please sign in to save your profile changes.')
            return redirect('account_login')
            
        u_form = UserUpdateForm(initial={
            'first_name': 'Alex',
            'last_name': 'Morgan',
            'username': 'alex_morgan',
            'email': 'alex.morgan@phidimservice.com'
        })
        p_form = ProfileForm(initial={
            'bio': 'Senior Solutions Architect & Tech Enthusiast based in Kathmandu. Passionate about scalable distributed systems, industrial automation, and modern web architecture.',
            'phone_number': '9841234567',
            'latitude': '27.717245300000',
            'longitude': '85.323960500000',
            'is_active': True,
            'is_deleted': False,
            'is_verified': True
        })
        k_form = KYCForm(initial={
            'citizenship_number': '27-01-79-04512'
        })
        context = {
            'u_form': u_form,
            'p_form': p_form,
            'k_form': k_form,
            'profile': None,
            'kyc': None,
            'is_demo': True
        }
        
    return render(request, 'home/profile.html', context)