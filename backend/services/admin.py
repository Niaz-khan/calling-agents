from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "duration_minutes", "price", "active")
    list_filter = ("active", "organization")