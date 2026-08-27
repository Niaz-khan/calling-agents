from django.db import models


class Customer(models.Model):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="customers"
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=50, db_index=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    memory = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "phone_number"], name="uq_customer_org_phone"
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or self.phone_number