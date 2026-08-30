from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone_number", "organization", "email", "created_at")
    list_filter = ("organization",)
    search_fields = ("name", "phone_number", "email")