from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Profile
from .forms import ProfileForm, UserUpdateForm

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
    Supports authenticated editing and graceful preview.
    """
    if request.user.is_authenticated:
        user_profile, created = Profile.objects.get_or_create(user=request.user)
        
        if request.method == 'POST':
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileForm(request.POST, request.FILES, instance=user_profile)
            
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Profile successfully updated!')
                return redirect('profile')
            else:
                messages.error(request, 'Please check the form for errors and try again.')
        else:
            u_form = UserUpdateForm(instance=request.user)
            p_form = ProfileForm(instance=user_profile)
            
        context = {
            'u_form': u_form,
            'p_form': p_form,
            'profile': user_profile,
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
        context = {
            'u_form': u_form,
            'p_form': p_form,
            'profile': None,
            'is_demo': True
        }
        
    return render(request, 'home/profile.html', context)