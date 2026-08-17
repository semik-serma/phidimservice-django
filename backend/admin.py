from django.contrib import admin
from .models import Profile, KYC, ServiceCategory, ServiceRequest, CallSession, ChatMessage


class KYCInline(admin.StackedInline):
    model = KYC
    can_delete = False
    extra = 0
    max_num = 1


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [KYCInline]
    list_display = ('user', 'role', 'phone_number', 'is_online', 'is_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_online', 'availability_status', 'is_verified', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone_number', 'skills')
    readonly_fields = ('created_at', 'updated_at', 'location_updated_at')

    fieldsets = (
        ('Account & Role', {
            'fields': ('user', 'role', 'profile_picture', 'bio', 'phone_number')
        }),
        ('Technician Attributes', {
            'fields': ('skills', 'experience_years', 'hourly_rate', 'availability_status', 'rating', 'total_reviews'),
            'classes': ('collapse',),
        }),
        ('Location & Online Status', {
            'fields': (('latitude', 'longitude'), 'location_accuracy', 'location_updated_at', 'is_online', 'last_seen')
        }),
        ('Status & Verification', {
            'fields': ('is_active', 'is_verified', 'is_deleted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'citizenship_number', 'status', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('citizenship_number', 'profile__user__username')
    readonly_fields = ('submitted_at',)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'base_price', 'icon_class', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'customer', 'technician', 'status', 'priority', 'price_estimate', 'created_at')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('title', 'description', 'customer__username', 'technician__username', 'customer_address')
    readonly_fields = ('created_at', 'updated_at', 'accepted_at', 'started_at', 'completed_at', 'technician_location_updated_at')


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ('room_id', 'request', 'caller', 'receiver', 'status', 'duration_seconds', 'started_at')
    list_filter = ('status', 'started_at')
    search_fields = ('room_id', 'caller__username', 'receiver__username')
    readonly_fields = ('started_at', 'connected_at', 'ended_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'sender', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('message', 'sender__username')
    readonly_fields = ('created_at',)
