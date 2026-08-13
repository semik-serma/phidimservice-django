
# backend/signals.py

import requests

from django.core.files.base import ContentFile
from django.dispatch import receiver

from allauth.account.signals import user_signed_up

from .models import Profile


@receiver(user_signed_up)
def save_social_avatar(request, user, **kwargs):
    print("\n========== SOCIAL AVATAR DEBUG ==========")
    print(f"[1] User signed up: {user}")
    print(f"[1] User ID: {user.pk}")

    sociallogin = kwargs.get("sociallogin")

    if not sociallogin:
        print("[ERROR] No sociallogin object found.")
        return

    print(f"[2] Social provider: {sociallogin.account.provider}")
    print(f"[2] Social account UID: {sociallogin.account.uid}")

    extra_data = sociallogin.account.extra_data

    print(f"[3] Social account extra_data: {extra_data}")

    picture_url = extra_data.get("picture")

    if not picture_url:
        print("[ERROR] No 'picture' found in extra_data.")
        print(f"[DEBUG] Available keys: {list(extra_data.keys())}")
        return

    print(f"[4] Profile picture URL found: {picture_url}")

    try:
        profile, created = Profile.objects.get_or_create(user=user)

        print(
            f"[5] Profile {'created' if created else 'already exists'}: "
            f"profile_id={profile.pk}"
        )

    except Exception as e:
        print(f"[ERROR] Failed to get/create Profile: {e}")
        return

    try:
        print("[6] Downloading profile picture...")

        response = requests.get(
            picture_url,
            timeout=10,
        )

        print(f"[7] HTTP status: {response.status_code}")
        print(f"[7] Content-Type: {response.headers.get('Content-Type')}")
        print(f"[7] Content-Length: {len(response.content)} bytes")

        response.raise_for_status()

    except requests.RequestException as e:
        print(f"[ERROR] Failed to download profile picture: {e}")
        return

    try:
        filename = f"{user.pk}.jpg"

        print(f"[8] Saving profile picture...")
        print(f"[8] Filename: {filename}")
        print(f"[8] Existing profile_picture: {profile.profile_picture}")

        profile.profile_picture.save(
            filename,
            ContentFile(response.content),
            save=True,
        )

        print("[9] Profile picture saved successfully!")
        print(f"[9] Saved path: {profile.profile_picture.name}")

        try:
            print(f"[9] Saved URL: {profile.profile_picture.url}")
        except Exception as e:
            print(f"[WARNING] Could not get profile_picture.url: {e}")

    except Exception as e:
        print(f"[ERROR] Failed to save profile picture: {e}")
        return

    print("========== SOCIAL AVATAR DEBUG END ==========\n")
