"""Database-backed CMS for the public website.

Every public-facing model has ``enabled``/``order`` so content editors can
toggle and reorder without redeploying the frontend. Rich text is stored as
plain text or JSON data only — never raw HTML — so CMS fields cannot inject
markup/scripts.

The public API only ever returns published/enabled rows (``views_public``).
Mutation happens exclusively through the platform-admin API (``views_admin``).
"""

from django.conf import settings as django_settings
from django.db import models

DEFAULT_SECTIONS = [
    {"key": "hero", "enabled": True},
    {"key": "value_strip", "enabled": True},
    {"key": "problem", "enabled": True},
    {"key": "features", "enabled": True},
    {"key": "showcase", "enabled": True},
    {"key": "how_works", "enabled": True},
    {"key": "website", "enabled": True},
    {"key": "phone", "enabled": True},
    {"key": "api", "enabled": True},
    {"key": "use_cases", "enabled": True},
    {"key": "analytics", "enabled": True},
    {"key": "pricing", "enabled": True},
    {"key": "faq", "enabled": True},
    {"key": "cta", "enabled": True},
]

SECTION_LABELS = {
    "hero": "Hero",
    "value_strip": "Value strip",
    "problem": "Problem / solution",
    "features": "Features",
    "showcase": "Product showcase",
    "how_works": "How it works",
    "website": "Website widget",
    "phone": "Phone agent",
    "api": "API & integrations",
    "use_cases": "Use cases",
    "analytics": "Analytics",
    "pricing": "Pricing",
    "faq": "FAQ",
    "cta": "Final CTA",
}


class SingletonManager(models.Manager):
    """Return/create the single SiteSettings / LandingPage row (pk=1)."""

    def load(self):
        obj, _ = self.get_or_create(pk=1)
        return obj


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SiteSettings(TimestampedModel):
    """Global site/branding configuration (single row)."""

    objects = SingletonManager()

    is_published = models.BooleanField(default=True)
    site_name = models.CharField(max_length=255, default="AI Call Agent")
    logo = models.CharField(max_length=500, blank=True, default="")
    favicon = models.CharField(max_length=500, blank=True, default="")
    website_url = models.CharField(max_length=500, blank=True, default="")
    font_family = models.CharField(
        max_length=64, choices=(("Inter", "Inter"), ("System", "System")), default="Inter"
    )
    primary_color = models.CharField(max_length=20, default="#2E7CF6")
    secondary_color = models.CharField(max_length=20, default="#14B8A6")
    contact_email = models.EmailField(blank=True, default="")
    support_email = models.EmailField(blank=True, default="")
    social_links = models.JSONField(
        default=list, blank=True, help_text="List of {label, url} objects."
    )
    announcement_enabled = models.BooleanField(default=False)
    announcement_text = models.CharField(max_length=500, blank=True, default="")

    meta_title = models.CharField(max_length=255, blank=True, default="")
    meta_description = models.TextField(blank=True, default="")
    og_title = models.CharField(max_length=255, blank=True, default="")
    og_description = models.TextField(blank=True, default="")
    og_image = models.CharField(max_length=500, blank=True, default="")
    canonical_url = models.CharField(max_length=500, blank=True, default="")
    robots = models.CharField(max_length=128, default="index,follow")

    def __str__(self):
        return self.site_name


class LandingPage(TimestampedModel):
    """Publishable landing-page content + section builder (single row)."""

    objects = SingletonManager()

    is_published = models.BooleanField(default=False)
    sections = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of {key, enabled}. Keys from SECTION_LABELS.",
    )

    hero_enabled = models.BooleanField(default=True)
    hero_badge = models.CharField(max_length=255, blank=True, default="")
    hero_title = models.CharField(
        max_length=255, default="Your AI employee for every customer conversation."
    )
    hero_subtitle = models.TextField(
        default=(
            "Answer calls, chat with website visitors, book appointments, qualify "
            "customers, and hand off to your team — automatically."
        )
    )
    hero_primary_cta = models.CharField(max_length=64, default="Start for free")
    hero_secondary_cta = models.CharField(max_length=64, default="Book a demo")

    value_strip_title = models.CharField(max_length=255, default="One AI agent. Every customer channel.")
    value_strip_items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of short channel labels, e.g. PHONE, WEBSITE, APPOINTMENTS.",
    )

    problem_title = models.CharField(
        max_length=255, default="Your team shouldn't have to answer the same questions all day."
    )
    problem_items = models.JSONField(
        default=list,
        blank=True,
        help_text="List of common business problems.",
    )
    solution_title = models.CharField(
        max_length=255, default="Let your AI agent handle the routine. Let your team handle what matters."
    )
    solution_text = models.TextField(
        default=(
            "Your AI agent answers the repetitive questions, books appointments, and "
            "captures every lead — then hands the conversations that matter to your team."
        )
    )

    features_title = models.CharField(max_length=255, default="Everything a great receptionist does, on autopilot.")
    features_subtitle = models.TextField(
        default="Purpose-built tools that turn one AI agent into your busiest employee."
    )

    showcase_title = models.CharField(
        max_length=255, default="Everything your AI employee needs to run the conversation."
    )
    showcase_subtitle = models.TextField(
        default="Calls, customers, appointments, agent and analytics — from one clean workspace."
    )

    how_works_title = models.CharField(max_length=255, default="How it works")
    how_works_steps = models.JSONField(
        default=list,
        blank=True,
        help_text="List of {num, title, text} steps.",
    )

    website_section_title = models.CharField(
        max_length=255, default="Put your AI agent on your website in minutes."
    )
    website_section_text = models.TextField(
        default="Copy one snippet, paste it before </body>, and your agent is live."
    )
    website_section_cta = models.CharField(max_length=64, default="Create website agent")

    phone_section_title = models.CharField(max_length=255, default="Never miss a customer call again.")
    phone_section_text = models.TextField(
        default="Your agent answers, greets, converses, books, and transfers — on your schedule."
    )
    phone_section_cta = models.CharField(max_length=64, default="Set up phone agent")

    api_section_title = models.CharField(
        max_length=255, default="Put your AI agent inside your own products."
    )
    api_section_text = models.TextField(
        default=(
            "Expose your agent as a conversation API. Custom apps, CRMs and support "
            "tools can hand conversations to your AI — no phone number or website needed."
        )
    )
    api_section_cta = models.CharField(max_length=64, default="Explore the API")

    use_cases_title = models.CharField(max_length=255, default="Built for the way service businesses work.")
    use_cases_subtitle = models.TextField(
        default="Configure your agent for the questions your customers actually ask."
    )

    analytics_title = models.CharField(max_length=255, default="Know what happened on every conversation.")
    analytics_subtitle = models.TextField(
        default="Conversations, appointments, transfers and outcomes — all in one view."
    )

    pricing_title = models.CharField(max_length=255, default="Simple pricing for every stage.")
    pricing_subtitle = models.TextField(default="Pricing coming soon. Start free while you set up.")
    pricing_disclaimer = models.CharField(max_length=500, blank=True, default="")

    faq_title = models.CharField(max_length=255, default="Frequently asked questions")
    faq_subtitle = models.TextField(blank=True, default="")

    cta_title = models.CharField(max_length=255, default="Give your business an AI employee.")
    cta_subtitle = models.TextField(
        default="Start with one agent. Connect your business. Let it handle the conversations."
    )
    cta_primary = models.CharField(max_length=64, default="Create your AI agent")
    cta_secondary = models.CharField(max_length=64, default="View demo")

    def __str__(self):
        return "Landing page"

    def sections_for(self):
        """Resolve stored section config against known sections, preserving order."""
        stored = {
            item["key"]: bool(item.get("enabled"))
            for item in self.sections
            if isinstance(item, dict) and "key" in item
        }
        ordered = [item["key"] for item in self.sections if isinstance(item, dict)]
        if not stored:
            stored = {item["key"]: item["enabled"] for item in DEFAULT_SECTIONS}
        if not ordered:
            ordered = [item["key"] for item in DEFAULT_SECTIONS]
        # Append default sections a stored config predates (e.g. "api") so
        # newly added sections surface without a manual edit by the admin.
        for default in DEFAULT_SECTIONS:
            if default["key"] not in ordered:
                ordered.append(default["key"])
        merged = []
        for key in ordered:
            if key in SECTION_LABELS:
                merged.append(
                    {"key": key, "label": SECTION_LABELS[key], "enabled": stored.get(key, True)}
                )
        return merged


class OrderedContentModel(models.Model):
    order = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["order", "id"]


class FeatureSection(OrderedContentModel, TimestampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class UseCase(OrderedContentModel, TimestampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Testimonial(OrderedContentModel, TimestampedModel):
    name = models.CharField(max_length=255)
    company = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=255, blank=True, default="")
    quote = models.TextField()
    avatar = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} — {self.company}"


class PricingPlan(OrderedContentModel, TimestampedModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True, default="")
    price = models.CharField(max_length=128, default="Coming soon")
    billing_period = models.CharField(max_length=64, blank=True, default="")
    features = models.JSONField(default=list, blank=True)
    cta_text = models.CharField(max_length=64, default="Get started")
    highlighted = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class FAQ(OrderedContentModel, TimestampedModel):
    question = models.CharField(max_length=500)
    answer = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.question


class NavigationItem(OrderedContentModel, TimestampedModel):
    label = models.CharField(max_length=255)
    url = models.CharField(max_length=500)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class FooterSection(OrderedContentModel, TimestampedModel):
    title = models.CharField(max_length=255)
    links = models.JSONField(
        default=list, blank=True, help_text="List of {label, url} objects."
    )

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class CmsVersion(models.Model):
    """One published snapshot of the whole public site.

    Editing always writes drafts into the live tables above. Publishing builds
    a full snapshot of every CMS table and stores it here; the public API only
    ever serves the latest ``is_current`` snapshot, never draft rows. Each
    publish creates a new row, giving lightweight version history.
    """

    number = models.PositiveIntegerField(default=1)
    published_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cms_versions_published",
    )
    published_at = models.DateTimeField(auto_now_add=True)
    summary = models.TextField(blank=True, default="")
    snapshot = models.JSONField(
        default=dict,
        blank=True,
        help_text="Serialized site settings, landing page and ordered collections.",
    )
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-number"]

    def __str__(self):
        return f"v{self.number}"


class CmsActivity(models.Model):
    """Audit feed of CMS actions (draft saves, publish, unpublish, restore)."""

    class Action(models.TextChoices):
        DRAFT_SAVED = "draft_saved", "Draft saved"
        SECTIONS_UPDATED = "sections_updated", "Sections updated"
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        DELETED = "deleted", "Deleted"
        PUBLISHED = "published", "Published"
        UNPUBLISHED = "unpublished", "Unpublished"
        RESTORED = "restored", "Version restored"

    actor = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cms_activity",
    )
    action = models.CharField(max_length=32, choices=Action.choices)
    resource = models.CharField(max_length=255)
    detail = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} — {self.resource}"