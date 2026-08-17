from django.urls import path
from . import views

urlpatterns = [
    # Public Website Routes
    path('', views.home, name='index'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('profile/', views.profile, name='profile'),
    path('product/<str:product_id>/', views.product_detail, name='product_detail'),

    # Role Dashboards
    path('dashboard/', views.dashboard_redirect, name='dashboard'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
    path('dashboard/technician/', views.technician_dashboard, name='technician_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),

    # REST / AJAX API Routes
    path('api/auth/set-pending-role/', views.api_set_pending_role, name='api_set_pending_role'),
    path('api/location/update/', views.api_update_location, name='api_update_location'),
    path('api/requests/<int:request_id>/tracking/', views.api_get_request_tracking, name='api_get_request_tracking'),
    path('api/requests/create/', views.api_create_service_request, name='api_create_service_request'),
    path('api/requests/<int:request_id>/status/', views.api_update_request_status, name='api_update_request_status'),
    path('api/technician/toggle-status/', views.api_toggle_technician_status, name='api_toggle_technician_status'),
    path('api/call/session/<int:request_id>/', views.api_initiate_call_session, name='api_initiate_call_session'),
    path('api/call/session/<str:room_id>/status/', views.api_update_call_status, name='api_update_call_status'),
    path('api/admin/kyc/<int:kyc_id>/action/', views.api_admin_kyc_action, name='api_admin_kyc_action'),
]
