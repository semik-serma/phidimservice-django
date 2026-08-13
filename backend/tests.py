from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from backend.models import Profile
from backend.forms import ProfileForm, UserUpdateForm
from decimal import Decimal

class ProfileTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='Password123!',
            first_name='Test',
            last_name='User'
        )
        self.profile = Profile.objects.create(
            user=self.user,
            bio='Initial test bio',
            phone_number='9801234567',
            latitude=Decimal('27.717245000000'),
            longitude=Decimal('85.323960000000'),
            is_active=True,
            is_deleted=False,
            is_verified=True
        )

    def test_anonymous_profile_view_preview(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Manage Your')
        self.assertContains(response, 'Personal & Identity')
        self.assertContains(response, 'Geolocation & Regional Coordinates')


    def test_authenticated_profile_view_get(self):
        self.client.login(username='testuser', password='Password123!')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Initial test bio')
        self.assertContains(response, '9801234567')

    def test_authenticated_profile_view_post(self):
        self.client.login(username='testuser', password='Password123!')
        data = {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'username': 'testuser',
            'email': 'updated@example.com',
            'bio': 'Updated professional bio description.',
            'phone_number': '9841999999',
            'latitude': '28.123456789012',
            'longitude': '84.987654321098',
            'is_active': 'on',
            'is_verified': 'on',
        }
        response = self.client.post(reverse('profile'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(self.user.first_name, 'UpdatedFirst')
        self.assertEqual(self.user.email, 'updated@example.com')
        self.assertEqual(self.profile.bio, 'Updated professional bio description.')
        self.assertEqual(self.profile.phone_number, '9841999999')
        self.assertEqual(self.profile.latitude, Decimal('28.123456789012'))
        self.assertEqual(self.profile.longitude, Decimal('84.987654321098'))
        self.assertTrue(self.profile.is_active)
        self.assertTrue(self.profile.is_verified)
        self.assertFalse(self.profile.is_deleted)

    def test_phone_number_validation(self):
        form = ProfileForm(data={
            'phone_number': '12345',  # Invalid length
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
