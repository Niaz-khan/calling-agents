from django.db import models
from django.utils import timezone


class ConversationChannel(models.TextChoices):
    PHONE = "phone", "phone"
    WEBSITE = "website", "website"
    API = "api", "api"


class ConversationStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    CLOSED = "CLOSED", "Closed"


class ConversationOutcome(models.TextChoices):
    """Mirrors the legacy ``calloutcome`` enum (values stored uppercase)."""

    APPOINTMENT_BOOKED = "APPOINTMENT_BOOKED", "Appointment booked"
    APPOINTMENT_REQUESTED = "APPOINTMENT_REQUESTED", "Appointment requested"
    INFORMATION_PROVIDED = "INFORMATION_PROVIDED", "Information provided"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED", "Callback requested"
    TRANSFERRED_TO_HUMAN = "TRANSFERRED_TO_HUMAN", "Transferred to human"
    NO_RESOLUTION = "NO_RESOLUTION", "No resolution"
    CUSTOMER_HUNG_UP = "CUSTOMER_HUNG_UP", "Customer hung up"
    UNKNOWN = "UNKNOWN", "Unknown"


class PhoneCallDirection(models.TextChoices):
    INBOUND = "INBOUND", "Inbound"
    OUTBOUND = "OUTBOUND", "Outbound"


class PhoneCallStatus(models.TextChoices):
    """Telephony provider status (legacy ``callstatus`` enum)."""

    RINGING = "RINGING", "Ringing"
    IN_PROGRESS = "IN_PROGRESS", "In progress"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    TRANSFERRED = "TRANSFERRED", "Transferred"


class Conversation(models.Model):
    """Channel-agnostic session shared by phone, website and API.

    The telephony-only fields live in the one-to-one ``PhoneCall`` profile so
    every channel persists through the same message/transcript/summary path.
    """

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="conversations"
    )
    agent = models.ForeignKey(
        "agents.Agent", on_delete=models.CASCADE, related_name="conversations"
    )
    deployment = models.ForeignKey(
        "agents.AgentDeployment",
        on_delete=models.SET_NULL,
        related_name="conversations",
        blank=True,
        null=True,
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.SET_NULL,
        related_name="conversations",
        blank=True,
        null=True,
    )
    channel = models.CharField(
        max_length=16,
        choices=ConversationChannel.choices,
        default=ConversationChannel.PHONE,
        db_index=True,
    )
    visitor_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        db_index=True,
        help_text="Web/API visitor session id, so a returning visitor continues "
        "the same open conversation.",
    )
    status = models.CharField(
        max_length=16,
        choices=ConversationStatus.choices,
        default=ConversationStatus.OPEN,
        db_index=True,
    )
    outcome = models.CharField(
        max_length=32, choices=ConversationOutcome.choices, blank=True, null=True
    )
    transcript = models.TextField(blank=True, null=True)
    summary = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.channel} conversation #{self.id}"

    def close(self, ended_at=None):
        self.status = ConversationStatus.CLOSED
        self.ended_at = ended_at or timezone.now()


class ConversationMessage(models.Model):
    class Role(models.TextChoices):
        USER = "USER", "User"
        ASSISTANT = "ASSISTANT", "Assistant"
        SYSTEM = "SYSTEM", "System"
        TOOL = "TOOL", "Tool"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    tool_call_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role} @ {self.conversation_id}"


class PhoneCall(models.Model):
    """Telephony-only profile of a ``Conversation(channel="phone")``."""

    conversation = models.OneToOneField(
        Conversation, on_delete=models.CASCADE, related_name="phone_call"
    )
    phone_number = models.ForeignKey(
        "telephony.PhoneNumber",
        on_delete=models.SET_NULL,
        related_name="calls",
        blank=True,
        null=True,
    )
    provider_call_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    stream_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Per-call secret embedded in the Twilio media stream URL so an "
        "unauthenticated websocket cannot open a stream for a call it does not own.",
    )
    direction = models.CharField(
        max_length=16,
        choices=PhoneCallDirection.choices,
        default=PhoneCallDirection.INBOUND,
    )
    caller_number = models.CharField(max_length=50, blank=True, default="")
    recording_url = models.TextField(blank=True, null=True)
    provider_status = models.CharField(
        max_length=16,
        choices=PhoneCallStatus.choices,
        default=PhoneCallStatus.RINGING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"phone call #{self.conversation_id}"