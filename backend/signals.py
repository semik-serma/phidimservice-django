import requests
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.account.signals import user_signed_up

from .models import Profile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Ensure every User always has an associated Profile.
    If the user is superuser, set role to admin.
    """
    if created:
        role = 'admin' if instance.is_superuser or instance.is_staff else 'customer'
        Profile.objects.get_or_create(user=instance, defaults={'role': role})
    else:
        try:
            if instance.is_superuser and instance.profile.role != 'admin':
                instance.profile.role = 'admin'
                instance.profile.save()
        except Exception:
            pass


@receiver(user_signed_up)
def save_social_avatar_and_details(request, user, **kwargs):
    """
    Extracts social avatar, first/last names, and syncs to user Profile
    across Google, GitHub, and Facebook.
    """
    sociallogin = kwargs.get("sociallogin")
    if not sociallogin:
        return

    provider = sociallogin.account.provider
    extra_data = sociallogin.account.extra_data or {}
    picture_url = None

    if provider == 'google':
        picture_url = extra_data.get("picture")
    elif provider == 'github':
        picture_url = extra_data.get("avatar_url")
        if not user.first_name and extra_data.get("name"):
            parts = extra_data["name"].split(" ", 1)
            user.first_name = parts[0]
            if len(parts) > 1:
                user.last_name = parts[1]
            user.save()
    elif provider == 'facebook':
        picture_obj = extra_data.get("picture")
        if isinstance(picture_obj, dict):
            picture_url = picture_obj.get("data", {}).get("url")
        else:
            picture_url = f"https://graph.facebook.com/{sociallogin.account.uid}/picture?type=large"

    profile, _ = Profile.objects.get_or_create(user=user)

    # Check if role was chosen in session (e.g. from signup page)
    if request and hasattr(request, 'session'):
        chosen_role = request.session.get('pending_signup_role')
        if chosen_role in ['customer', 'technician']:
            profile.role = chosen_role
            profile.save()

    if picture_url:
        try:
            response = requests.get(picture_url, timeout=10)
            if response.status_code == 200:
                filename = f"avatar_{user.pk}.jpg"
                profile.profile_picture.save(
                    filename,
                    ContentFile(response.content),
                    save=True,
                )
        except Exception as e:
            print(f"[WARNING] Could not save avatar from {provider}: {e}")
