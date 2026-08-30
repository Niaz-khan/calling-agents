from django.contrib import admin

from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "customer_phone", "agent", "organization", "start_time", "end_time", "status")
    list_filter = ("status", "organization")
    search_fields = ("customer_name", "customer_phone")