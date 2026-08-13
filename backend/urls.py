from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('contact/', views.contact, name='contact'),
    path('profile/', views.profile, name='profile'),
    path('product/<str:product_id>/', views.product_detail, name='product_detail'),
]

