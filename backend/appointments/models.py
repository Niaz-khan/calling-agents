from django.db import models


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", "Scheduled"
        CANCELLED = "CANCELLED", "Cancelled"
        COMPLETED = "COMPLETED", "Completed"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="appointments"
    )
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="appointments"
    )
    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.SET_NULL,
        related_name="appointments",
        blank=True,
        null=True,
    )
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=50)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.SCHEDULED
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.customer_name} @ {self.start_time}"