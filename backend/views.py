import json
import uuid
import math
from decimal import Decimal
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.models import User

from .models import Profile, KYC, ServiceCategory, ServiceRequest, CallSession, ChatMessage
from .forms import ProfileForm, UserUpdateForm, KYCForm, ServiceRequestForm


# ----------------------------------------------------
# 1. PUBLIC PAGES
# ----------------------------------------------------
def home(request):
    categories = ServiceCategory.objects.filter(is_active=True)[:6]
    return render(request, 'home/index.html', {'categories': categories})


def about(request):
    return render(request, 'home/about.html')


def services(request):
    categories = ServiceCategory.objects.filter(is_active=True)
    return render(request, 'home/services.html', {'categories': categories})


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
            'latitude': Decimal('27.717245300000'),
            'longitude': Decimal('85.323960500000'),
            'is_active': True,
            'is_deleted': False,
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


# ----------------------------------------------------
# 2. ROLE-BASED DASHBOARD ROUTING & VIEWS
# ----------------------------------------------------
@login_required
def dashboard_redirect(request):
    """
    Intelligently routes the authenticated user to their role-specific dashboard.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.role == 'technician':
        return redirect('technician_dashboard')
    elif profile.role == 'admin' or request.user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('customer_dashboard')


@login_required
def customer_dashboard(request):
    """
    Customer Dashboard: View active requests, live technician tracking,
    request booking modal, history, and video calling.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.role == 'technician':
        return redirect('technician_dashboard')

    active_requests = ServiceRequest.objects.filter(
        customer=request.user,
        status__in=['PENDING', 'ACCEPTED', 'EN_ROUTE', 'IN_PROGRESS']
    ).order_by('-created_at')

    past_requests = ServiceRequest.objects.filter(
        customer=request.user,
        status__in=['COMPLETED', 'CANCELLED']
    ).order_by('-created_at')[:20]

    categories = ServiceCategory.objects.filter(is_active=True)

    context = {
        'profile': profile,
        'active_requests': active_requests,
        'past_requests': past_requests,
        'categories': categories,
        'total_requests': active_requests.count() + past_requests.count(),
        'completed_count': past_requests.filter(status='COMPLETED').count(),
    }
    return render(request, 'dashboard/customer_dashboard.html', context)


@login_required
def technician_dashboard(request):
    """
    Technician Dashboard: View assigned active jobs, available requests pool,
    broadcast live GPS telemetry, start/receive video calls, and manage earnings.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.role == 'customer' and not request.user.is_superuser:
        messages.info(request, 'Switching account view to technician.')
        profile.role = 'technician'
        profile.save()

    active_job = ServiceRequest.objects.filter(
        technician=request.user,
        status__in=['ACCEPTED', 'EN_ROUTE', 'IN_PROGRESS']
    ).first()

    available_jobs = ServiceRequest.objects.filter(
        status='PENDING'
    ).order_by('-priority', '-created_at')[:15]

    completed_jobs = ServiceRequest.objects.filter(
        technician=request.user,
        status='COMPLETED'
    ).order_by('-completed_at')[:20]

    total_earnings = sum(job.final_price or job.price_estimate or 0 for job in completed_jobs)

    context = {
        'profile': profile,
        'active_job': active_job,
        'available_jobs': available_jobs,
        'completed_jobs': completed_jobs,
        'total_earnings': total_earnings,
        'completed_count': completed_jobs.count(),
    }
    return render(request, 'dashboard/technician_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """
    Admin Dashboard: Platform metrics, user & technician management,
    KYC document verification, active jobs tracking, and call audits.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if profile.role != 'admin' and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'Access restricted to administrators.')
        return redirect('customer_dashboard')

    total_users = User.objects.count()
    total_technicians = Profile.objects.filter(role='technician').count()
    total_requests = ServiceRequest.objects.count()
    active_requests = ServiceRequest.objects.filter(status__in=['PENDING', 'ACCEPTED', 'EN_ROUTE', 'IN_PROGRESS'])
    pending_kyc = KYC.objects.filter(status='pending').select_related('profile__user')
    technicians = Profile.objects.filter(role='technician').select_related('user')[:20]
    recent_requests = ServiceRequest.objects.all().order_by('-created_at')[:15]

    context = {
        'profile': profile,
        'total_users': total_users,
        'total_technicians': total_technicians,
        'total_requests': total_requests,
        'active_jobs_count': active_requests.count(),
        'pending_kyc': pending_kyc,
        'technicians': technicians,
        'recent_requests': recent_requests,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# ----------------------------------------------------
# 3. REST / AJAX API ENDPOINTS
# ----------------------------------------------------
@csrf_exempt
@require_POST
def api_set_pending_role(request):
    """
    Temporarily store role preference in session for OAuth registration.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        role = data.get('role', 'customer')
        if role in ['customer', 'technician']:
            request.session['pending_signup_role'] = role
            return JsonResponse({'success': True, 'role': role})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'success': False, 'error': 'Invalid role'}, status=400)


@login_required
@require_POST
def api_update_location(request):
    """
    Secure endpoint to update authenticated user's GPS coordinates.
    Also propagates technician location to active assigned jobs.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        lat = data.get('latitude')
        lng = data.get('longitude')
        accuracy = data.get('accuracy')

        if lat is None or lng is None:
            return JsonResponse({'success': False, 'error': 'Coordinates required'}, status=400)

        profile = request.user.profile
        profile.latitude = Decimal(str(lat))
        profile.longitude = Decimal(str(lng))
        if accuracy is not None:
            profile.location_accuracy = float(accuracy)
        profile.location_updated_at = timezone.now()
        profile.is_online = True
        profile.save()

        # If technician has active job, update the job telemetry
        if profile.role == 'technician':
            active_job = ServiceRequest.objects.filter(
                technician=request.user,
                status__in=['ACCEPTED', 'EN_ROUTE', 'IN_PROGRESS']
            ).first()
            if active_job:
                active_job.technician_latitude = profile.latitude
                active_job.technician_longitude = profile.longitude
                active_job.technician_location_updated_at = timezone.now()
                active_job.save(update_fields=['technician_latitude', 'technician_longitude', 'technician_location_updated_at'])

        return JsonResponse({
            'success': True,
            'latitude': float(profile.latitude),
            'longitude': float(profile.longitude),
            'updated_at': profile.location_updated_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in meters between two points on earth.
    """
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371000 # Earth radius in meters
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    delta_phi = math.radians(float(lat2) - float(lat1))
    delta_lambda = math.radians(float(lon2) - float(lon1))
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c)


@login_required
@require_GET
def api_get_request_tracking(request, request_id):
    """
    Returns live coordinates and status for an authorized service request.
    Only the customer, assigned technician, or an admin can access this data.
    """
    req = get_object_or_404(ServiceRequest, id=request_id)
    user = request.user

    if user != req.customer and user != req.technician and not user.is_staff:
        return HttpResponseForbidden("Unauthorized to view this service location data.")

    dist_meters = None
    if req.customer_latitude and req.technician_latitude:
        dist_meters = haversine_distance(
            req.customer_latitude, req.customer_longitude,
            req.technician_latitude, req.technician_longitude
        )

    tech_data = None
    if req.technician:
        tech_profile = getattr(req.technician, 'profile', None)
        tech_data = {
            'id': req.technician.id,
            'name': req.technician.get_full_name() or req.technician.username,
            'avatar': tech_profile.display_avatar if tech_profile else '',
            'phone': tech_profile.phone_number if tech_profile else '',
            'rating': float(tech_profile.rating) if tech_profile else 5.0,
            'latitude': float(req.technician_latitude) if req.technician_latitude else (float(tech_profile.latitude) if tech_profile and tech_profile.latitude else None),
            'longitude': float(req.technician_longitude) if req.technician_longitude else (float(tech_profile.longitude) if tech_profile and tech_profile.longitude else None),
            'location_updated_at': req.technician_location_updated_at.isoformat() if req.technician_location_updated_at else None,
        }

    return JsonResponse({
        'success': True,
        'request_id': req.id,
        'title': req.title,
        'status': req.status,
        'status_display': req.get_status_display(),
        'priority': req.priority,
        'customer': {
            'id': req.customer.id,
            'name': req.customer.get_full_name() or req.customer.username,
            'phone': req.customer_phone or (req.customer.profile.phone_number if hasattr(req.customer, 'profile') else ''),
            'address': req.customer_address,
            'latitude': float(req.customer_latitude) if req.customer_latitude else None,
            'longitude': float(req.customer_longitude) if req.customer_longitude else None,
        },
        'technician': tech_data,
        'distance_meters': dist_meters,
        'distance_formatted': f"{round(dist_meters/1000, 2)} km" if dist_meters and dist_meters >= 1000 else (f"{dist_meters} m" if dist_meters else "Calculating..."),
        'price_estimate': float(req.price_estimate) if req.price_estimate else None,
    })


@login_required
@require_POST
def api_create_service_request(request):
    """
    Create a new on-demand service request.
    """
    try:
        data = json.loads(request.body.decode('utf-8'))
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        category_id = data.get('category_id')
        service_type = data.get('service_type', 'Standard Service')
        priority = data.get('priority', 'standard')
        address = data.get('address', '')
        phone = data.get('phone', '')
        lat = data.get('latitude')
        lng = data.get('longitude')
        price_estimate = data.get('price_estimate')

        if not title or not description:
            return JsonResponse({'success': False, 'error': 'Title and description are required'}, status=400)

        category = ServiceCategory.objects.filter(id=category_id).first() if category_id else None

        req = ServiceRequest.objects.create(
            customer=request.user,
            category=category,
            title=title,
            service_type=service_type,
            description=description,
            priority=priority,
            customer_address=address,
            customer_phone=phone or request.user.profile.phone_number,
            customer_latitude=Decimal(str(lat)) if lat is not None else request.user.profile.latitude,
            customer_longitude=Decimal(str(lng)) if lng is not None else request.user.profile.longitude,
            price_estimate=Decimal(str(price_estimate)) if price_estimate else (category.base_price if category else Decimal('500.00')),
            status='PENDING'
        )

        return JsonResponse({
            'success': True,
            'request_id': req.id,
            'title': req.title,
            'status': req.status,
            'message': 'Service request created successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_update_request_status(request, request_id):
    """
    Updates the lifecycle status of a service request.
    """
    req = get_object_or_404(ServiceRequest, id=request_id)
    user = request.user

    try:
        data = json.loads(request.body.decode('utf-8'))
        new_status = data.get('status')

        valid_statuses = ['ACCEPTED', 'EN_ROUTE', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status choice'}, status=400)

        # Technician accepts job
        if new_status == 'ACCEPTED':
            if req.status != 'PENDING':
                return JsonResponse({'success': False, 'error': 'This job is no longer available'}, status=400)
            req.technician = user
            req.accepted_at = timezone.now()
            req.status = 'ACCEPTED'
            # Initialize technician location from their current profile
            if user.profile.latitude:
                req.technician_latitude = user.profile.latitude
                req.technician_longitude = user.profile.longitude
                req.technician_location_updated_at = timezone.now()
            req.save()
            return JsonResponse({'success': True, 'status': req.status, 'message': 'Job accepted successfully!'})

        # Actions on active job
        if user == req.technician:
            if new_status == 'EN_ROUTE':
                req.status = 'EN_ROUTE'
            elif new_status == 'IN_PROGRESS':
                req.status = 'IN_PROGRESS'
                req.started_at = timezone.now()
            elif new_status == 'COMPLETED':
                req.status = 'COMPLETED'
                req.completed_at = timezone.now()
                final_price = data.get('final_price')
                if final_price:
                    req.final_price = Decimal(str(final_price))
            req.save()
            return JsonResponse({'success': True, 'status': req.status, 'message': f'Status updated to {req.get_status_display()}'})

        # Customer cancels
        if user == req.customer and new_status == 'CANCELLED':
            if req.status in ['PENDING', 'ACCEPTED']:
                req.status = 'CANCELLED'
                req.save()
                return JsonResponse({'success': True, 'status': req.status, 'message': 'Request cancelled'})
            else:
                return JsonResponse({'success': False, 'error': 'Cannot cancel request once technician is en route or work has started'}, status=400)

        # Admin override
        if user.is_staff or user.profile.role == 'admin':
            req.status = new_status
            req.save()
            return JsonResponse({'success': True, 'status': req.status, 'message': 'Status updated by admin'})

        return HttpResponseForbidden("Unauthorized to modify this service request.")
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_toggle_technician_status(request):
    """
    Toggle technician online/availability state.
    """
    profile = request.user.profile
    try:
        data = json.loads(request.body.decode('utf-8'))
        is_online = data.get('is_online')
        availability = data.get('availability_status')

        if is_online is not None:
            profile.is_online = bool(is_online)
        if availability in ['available', 'busy', 'offline']:
            profile.availability_status = availability
        profile.save()

        return JsonResponse({
            'success': True,
            'is_online': profile.is_online,
            'availability_status': profile.availability_status
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ----------------------------------------------------
# 4. VIDEO CALLING API ENDPOINTS
# ----------------------------------------------------
@login_required
@require_POST
def api_initiate_call_session(request, request_id):
    """
    Initializes a WebRTC Call Session linked to a verified ServiceRequest.
    Ensures arbitrary callers cannot call arbitrary users.
    """
    req = get_object_or_404(ServiceRequest, id=request_id)
    user = request.user

    # Determine caller and receiver
    if user == req.customer:
        if not req.technician:
            return JsonResponse({'success': False, 'error': 'No technician is currently assigned to this request'}, status=400)
        receiver = req.technician
    elif user == req.technician:
        receiver = req.customer
    else:
        return HttpResponseForbidden("You are not a participant in this service request.")

    room_id = f"call_{req.id}_{uuid.uuid4().hex[:10]}"
    call_session = CallSession.objects.create(
        request=req,
        caller=user,
        receiver=receiver,
        room_id=room_id,
        status='initiated'
    )

    receiver_profile = getattr(receiver, 'profile', None)

    return JsonResponse({
        'success': True,
        'room_id': room_id,
        'request_id': req.id,
        'caller': {
            'id': user.id,
            'name': user.get_full_name() or user.username,
            'avatar': user.profile.display_avatar if hasattr(user, 'profile') else '',
        },
        'receiver': {
            'id': receiver.id,
            'name': receiver.get_full_name() or receiver.username,
            'avatar': receiver_profile.display_avatar if receiver_profile else '',
        },
        'service_title': req.title,
    })


@login_required
@require_POST
def api_update_call_status(request, room_id):
    """
    Update call session state (e.g. connected, ended, rejected).
    """
    call_session = get_object_or_404(CallSession, room_id=room_id)
    try:
        data = json.loads(request.body.decode('utf-8'))
        status = data.get('status')
        if status in ['connected', 'ended', 'rejected', 'missed']:
            call_session.status = status
            if status == 'connected':
                call_session.connected_at = timezone.now()
            elif status in ['ended', 'rejected']:
                call_session.ended_at = timezone.now()
                if call_session.connected_at:
                    delta = (call_session.ended_at - call_session.connected_at).total_seconds()
                    call_session.duration_seconds = max(0, int(delta))
            call_session.save()
            return JsonResponse({'success': True, 'status': call_session.status})
        return JsonResponse({'success': False, 'error': 'Invalid call status'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_admin_kyc_action(request, kyc_id):
    """
    Admin verification action on submitted technician KYC documents.
    """
    if not request.user.is_staff and request.user.profile.role != 'admin':
        return HttpResponseForbidden("Admin authorization required.")

    kyc = get_object_or_404(KYC, id=kyc_id)
    try:
        data = json.loads(request.body.decode('utf-8'))
        action = data.get('action')
        reason = data.get('reason', '')

        if action == 'approve':
            kyc.status = 'approved'
            kyc.reviewed_at = timezone.now()
            kyc.profile.is_verified = True
            kyc.profile.save()
            kyc.save()
            return JsonResponse({'success': True, 'message': 'KYC approved and technician verified.'})
        elif action == 'reject':
            kyc.status = 'rejected'
            kyc.rejection_reason = reason
            kyc.reviewed_at = timezone.now()
            kyc.profile.is_verified = False
            kyc.profile.save()
            kyc.save()
            return JsonResponse({'success': True, 'message': 'KYC application rejected.'})
        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)