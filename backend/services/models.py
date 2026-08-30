from django.db import models


class Service(models.Model):
    """A service the business offers and an agent can discuss/book."""

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="services"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration_minutes = models.PositiveIntegerField()
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )
    currency = models.CharField(max_length=3, default="USD")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name