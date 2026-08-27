from django.db import models


class PhoneNumber(models.Model):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="phone_numbers"
    )
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="phone_numbers"
    )
    phone_number = models.CharField(max_length=50, unique=True, db_index=True)
    provider = models.CharField(max_length=50)
    provider_number_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.phone_number