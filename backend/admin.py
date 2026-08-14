from django.contrib import admin
from .models import Profile, KYC


class KYCInline(admin.StackedInline):
    model = KYC
    can_delete = False
    extra = 0
    max_num = 1
    readonly_fields = ('citizenship_number','citizenship_front_image','citizenship_back_image')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    inlines = [KYCInline]
    list_display = ('user', 'phone_number', 'is_verified', 'is_active', 'is_deleted', 'created_at')
    list_filter = ('is_verified', 'is_active', 'is_deleted', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'profile_picture', 'bio', 'phone_number')
        }),
        ('Location Information', {
            'fields': (('latitude', 'longitude'),)
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
    list_display = ('id', 'profile', 'citizenship_number')
    search_fields = ('citizenship_number', 'profile__user__username')
    readonly_fields = ('citizenship_number','citizenship_front_image','citizenship_back_image','profile')

