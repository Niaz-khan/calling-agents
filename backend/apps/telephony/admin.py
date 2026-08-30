from django.contrib import admin

from .models import PhoneNumber


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("id", "phone_number", "agent", "organization", "provider", "is_active", "created_at")
    list_filter = ("provider", "is_active", "organization")
    search_fields = ("phone_number",)