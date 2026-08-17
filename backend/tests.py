from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from backend.models import Profile, KYC, ServiceCategory, ServiceRequest, CallSession
from backend.forms import ProfileForm, UserUpdateForm, KYCForm
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
import json


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
        self.profile = self.user.profile
        self.profile.bio = 'Initial test bio'
        self.profile.phone_number = '9801234567'
        self.profile.latitude = Decimal('27.717245000000')
        self.profile.longitude = Decimal('85.323960000000')
        self.profile.is_active = True
        self.profile.is_deleted = False
        self.profile.is_verified = True
        self.profile.save()

    def test_anonymous_profile_view_preview(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
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
            'role': 'customer',
            'is_active': 'on',
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


class PlatformUpgradeTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Create Customer
        self.customer = User.objects.create_user(
            username='cust_user',
            email='customer@example.com',
            password='Password123!',
            first_name='John',
            last_name='Customer'
        )
        self.customer_profile = self.customer.profile
        self.customer_profile.role = 'customer'
        self.customer_profile.latitude = Decimal('27.717200000000')
        self.customer_profile.longitude = Decimal('85.324000000000')
        self.customer_profile.save()

        # Create Technician
        self.tech = User.objects.create_user(
            username='tech_specialist',
            email='tech@example.com',
            password='Password123!',
            first_name='Ram',
            last_name='Sharma'
        )
        self.tech_profile = self.tech.profile
        self.tech_profile.role = 'technician'
        self.tech_profile.skills = 'Electrical, HVAC'
        self.tech_profile.latitude = Decimal('27.719000000000')
        self.tech_profile.longitude = Decimal('85.326000000000')
        self.tech_profile.save()

        # Create Category
        self.category = ServiceCategory.objects.create(
            name='Electrical Engineering',
            slug='electrical-test',
            base_price=Decimal('800.00')
        )

    def test_role_based_dashboard_redirect(self):
        # Customer logs in
        self.client.login(username='cust_user', password='Password123!')
        res = self.client.get(reverse('dashboard'))
        self.assertRedirects(res, reverse('customer_dashboard'))

        # Technician logs in
        self.client.login(username='tech_specialist', password='Password123!')
        res = self.client.get(reverse('dashboard'))
        self.assertRedirects(res, reverse('technician_dashboard'))

    def test_location_update_api(self):
        self.client.login(username='tech_specialist', password='Password123!')
        payload = {
            'latitude': 27.7205,
            'longitude': 85.3280,
            'accuracy': 12.5
        }
        res = self.client.post(
            reverse('api_update_location'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])

        self.tech_profile.refresh_from_db()
        self.assertEqual(float(self.tech_profile.latitude), 27.7205)
        self.assertEqual(float(self.tech_profile.longitude), 85.328)
        self.assertTrue(self.tech_profile.is_online)

    def test_service_request_lifecycle(self):
        # 1. Customer creates request
        self.client.login(username='cust_user', password='Password123!')
        create_payload = {
            'category_id': self.category.id,
            'title': 'Fuse Box Short Circuit',
            'description': 'Main breaker tripped and smells like smoke',
            'priority': 'urgent',
            'address': 'Ward 3, Phidim',
            'latitude': 27.7172,
            'longitude': 85.3240,
            'price_estimate': 850.00
        }
        res = self.client.post(
            reverse('api_create_service_request'),
            data=json.dumps(create_payload),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        req_id = data['request_id']

        req = ServiceRequest.objects.get(id=req_id)
        self.assertEqual(req.status, 'PENDING')
        self.assertEqual(req.customer, self.customer)

        # 2. Technician accepts request
        self.client.login(username='tech_specialist', password='Password123!')
        res = self.client.post(
            reverse('api_update_request_status', kwargs={'request_id': req_id}),
            data=json.dumps({'status': 'ACCEPTED'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, 'ACCEPTED')
        self.assertEqual(req.technician, self.tech)

        # 3. Technician updates status to EN_ROUTE
        res = self.client.post(
            reverse('api_update_request_status', kwargs={'request_id': req_id}),
            data=json.dumps({'status': 'EN_ROUTE'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, 'EN_ROUTE')

        # 4. Tracking API permissions check
        self.client.login(username='cust_user', password='Password123!')
        track_res = self.client.get(reverse('api_get_request_tracking', kwargs={'request_id': req_id}))
        self.assertEqual(track_res.status_code, 200)
        track_data = track_res.json()
        self.assertEqual(track_data['status'], 'EN_ROUTE')
        self.assertIsNotNone(track_data['technician'])

        # 5. Initiate WebRTC Call session
        call_res = self.client.post(reverse('api_initiate_call_session', kwargs={'request_id': req_id}))
        self.assertEqual(call_res.status_code, 200)
        call_data = call_res.json()
        self.assertTrue(call_data['success'])
        self.assertIn('call_', call_data['room_id'])
        self.assertEqual(call_data['receiver']['id'], self.tech.id)

        # 6. Complete Job
        self.client.login(username='tech_specialist', password='Password123!')
        comp_res = self.client.post(
            reverse('api_update_request_status', kwargs={'request_id': req_id}),
            data=json.dumps({'status': 'COMPLETED', 'final_price': 850.00}),
            content_type='application/json'
        )
        self.assertEqual(comp_res.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.status, 'COMPLETED')
        self.assertEqual(req.final_price, Decimal('850.00'))
