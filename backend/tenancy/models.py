from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)

    business_name = models.CharField(max_length=255, blank=True, null=True)
    timezone = models.CharField(max_length=64, default="UTC")
    business_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Weekly open schedule keyed by ISO weekday 1 (Mon)..7 (Sun), each an "
            "object like {\"start\": \"09:00\", \"end\": \"17:00\"}. Absent days "
            "are closed. An empty dict means always open."
        ),
    )
    contact_phone = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    website_url = models.URLField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return self.business_name or self.name


class OrganizationMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        STAFF = "STAFF", "Staff"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STAFF)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.user_id} @ {self.organization.name} ({self.role})"