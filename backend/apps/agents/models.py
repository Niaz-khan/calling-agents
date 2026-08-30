import secrets

from django.db import models


def generate_public_identifier() -> str:
    """Random, opaque public identifier for a deployment.

    128 bits of entropy (22 url-safe characters) behind a ``pub_`` prefix so
    public endpoints are clearly distinguishable from private ids.
    """
    return f"pub_{secrets.token_urlsafe(16)}"


class Agent(models.Model):
    class AfterHoursBehavior(models.TextChoices):
        CONTINUE = "continue", "Continue with AI"
        MESSAGE = "message", "Message and end call"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="agents"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    system_prompt = models.TextField()
    is_active = models.BooleanField(default=True)

    voice_greeting = models.CharField(max_length=500, blank=True, null=True)
    after_hours_behavior = models.CharField(
        max_length=24,
        choices=AfterHoursBehavior.choices,
        default=AfterHoursBehavior.MESSAGE,
    )
    recording_enabled = models.BooleanField(default=False)
    max_call_duration_minutes = models.PositiveIntegerField(blank=True, null=True)
    can_transfer = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class AgentDeploymentQuerySet(models.QuerySet):
    def resolve_public(self, identifier, channel=None):
        """Resolve a public identifier to a live, enabled deployment.

        Returns ``None`` for unknown, disabled, or channel-mismatched tokens so
        public endpoints can 404 without leaking whether an identifier exists.
        """
        qs = self.filter(
            public_identifier=identifier,
            enabled=True,
            organization__is_active=True,
            agent__is_active=True,
        )
        if channel is not None:
            qs = qs.filter(channel=channel)
        return qs.select_related("organization", "agent").first()


class AgentDeployment(models.Model):
    class Channel(models.TextChoices):
        PHONE = "phone", "Phone"
        WEBSITE = "website", "Website"
        API = "api", "API"
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="deployments"
    )
    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="deployments"
    )
    channel = models.CharField(
        max_length=16, choices=Channel.choices, default=Channel.WEBSITE
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    enabled = models.BooleanField(default=True)
    public_identifier = models.CharField(
        max_length=64, unique=True, editable=False, default=generate_public_identifier
    )
    allowed_domains = models.JSONField(default=list, blank=True)
    widget_title = models.CharField(max_length=255, blank=True, null=True)
    widget_primary_color = models.CharField(max_length=20, blank=True, null=True)
    welcome_message = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AgentDeploymentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel}:{self.agent_id}:{self.public_identifier}"