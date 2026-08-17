from django.conf import settings

def global_platform_settings(request):
    """
    Exposes platform-wide configuration settings and active user role
    to all rendered templates.
    """
    user_role = 'guest'
    user_profile = None
    if request.user.is_authenticated:
        try:
            user_profile = request.user.profile
            user_role = user_profile.role
        except Exception:
            user_role = 'customer'

    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'SOCKET_SERVER_URL': getattr(settings, 'SOCKET_SERVER_URL', 'http://localhost:5001'),
        'user_role': user_role,
        'current_user_profile': user_profile,
    }
