"""CMS draft/published workflow.

Editable tables (SiteSettings, LandingPage, ordered collections) are always the
*draft*. Publishing snapshots the whole site into a ``CmsVersion`` row
atomically; the public API reads only from the current published snapshot.

Restoring a version copies its snapshot back into the editable tables, creating
a new draft — it never republishes or overwrites silently.
"""

from django.db import transaction

from .models import (
    CmsActivity,
    CmsVersion,
    FAQ,
    FeatureSection,
    FooterSection,
    LandingPage,
    NavigationItem,
    PricingPlan,
    SiteSettings,
    Testimonial,
    UseCase,
)
from .serializers import (
    FAQSerializer,
    FeatureSectionSerializer,
    FooterSectionSerializer,
    LandingPageSerializer,
    NavigationItemSerializer,
    PricingPlanSerializer,
    PublicFAQSerializer,
    PublicFeatureSerializer,
    PublicFooterSectionSerializer,
    PublicLandingPageSerializer,
    PublicNavigationItemSerializer,
    PublicPricingPlanSerializer,
    PublicSiteSettingsSerializer,
    PublicTestimonialSerializer,
    PublicUseCaseSerializer,
    SiteSettingsSerializer,
    TestimonialSerializer,
    UseCaseSerializer,
)

COLLECTIONS = {
    "features": (FeatureSection, FeatureSectionSerializer, PublicFeatureSerializer),
    "use_cases": (UseCase, UseCaseSerializer, PublicUseCaseSerializer),
    "testimonials": (Testimonial, TestimonialSerializer, PublicTestimonialSerializer),
    "pricing": (PricingPlan, PricingPlanSerializer, PublicPricingPlanSerializer),
    "faqs": (FAQ, FAQSerializer, PublicFAQSerializer),
    "nav": (NavigationItem, NavigationItemSerializer, PublicNavigationItemSerializer),
    "footer": (FooterSection, FooterSectionSerializer, PublicFooterSectionSerializer),
}

COLLECTION_LABELS = {
    "features": "feature",
    "use_cases": "use case",
    "testimonials": "testimonial",
    "pricing": "pricing plan",
    "faqs": "FAQ",
    "nav": "nav item",
    "footer": "footer section",
}

COLLECTION_PLURALS = {
    "features": "features",
    "use_cases": "use cases",
    "testimonials": "testimonials",
    "pricing": "pricing plans",
    "faqs": "FAQs",
    "nav": "nav items",
    "footer": "footer sections",
}

SINGLETON_KEYS = {"id", "created_at", "updated_at", "is_published"}

SITE_GROUPS = {
    "Branding updated": [
        "site_name",
        "logo",
        "favicon",
        "website_url",
        "font_family",
        "primary_color",
        "secondary_color",
        "announcement_enabled",
        "announcement_text",
    ],
    "Contact details updated": ["contact_email", "support_email"],
    "Social links updated": ["social_links"],
    "SEO updated": [
        "meta_title",
        "meta_description",
        "og_title",
        "og_description",
        "og_image",
        "canonical_url",
        "robots",
    ],
}

LANDING_AREAS = [
    ("Hero changed", ["hero_enabled", "hero_badge", "hero_title", "hero_subtitle", "hero_primary_cta", "hero_secondary_cta"]),
    ("Value strip changed", ["value_strip_title", "value_strip_items"]),
    ("Problem section changed", ["problem_title", "problem_items", "solution_title", "solution_text"]),
    ("Features section changed", ["features_title", "features_subtitle"]),
    ("Showcase changed", ["showcase_title", "showcase_subtitle"]),
    ("How it works changed", ["how_works_title", "how_works_steps"]),
    ("Website widget changed", ["website_section_title", "website_section_text", "website_section_cta"]),
    ("Phone agent changed", ["phone_section_title", "phone_section_text", "phone_section_cta"]),
    ("Use cases changed", ["use_cases_title", "use_cases_subtitle"]),
    ("Analytics changed", ["analytics_title", "analytics_subtitle"]),
    ("Pricing modified", ["pricing_title", "pricing_subtitle", "pricing_disclaimer"]),
    ("FAQ changed", ["faq_title", "faq_subtitle"]),
    ("CTA changed", ["cta_title", "cta_subtitle", "cta_primary", "cta_secondary"]),
    ("Section layout changed", ["sections"]),
]


def log(action, resource, user=None, detail=None):
    """Record a CMS activity entry (platform admins only)."""
    CmsActivity.objects.create(
        actor=user if user and user.is_authenticated else None,
        action=action,
        resource=resource,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


def build_snapshot():
    """Serialized snapshot of every CMS table (draft truth + public subset)."""
    site = SiteSettings.objects.load()
    page = LandingPage.objects.load()
    collections = {}
    public_collections = {}
    for key, (model, serializer, public_serializer) in COLLECTIONS.items():
        rows = list(model.objects.all())
        collections[key] = serializer(rows, many=True).data
        public_collections[key] = public_serializer(
            [row for row in rows if row.enabled], many=True
        ).data
    return {
        "site": SiteSettingsSerializer(site).data,
        "landing": LandingPageSerializer(page).data,
        "collections": collections,
        "public": {
            "site": PublicSiteSettingsSerializer(site).data,
            "landing": PublicLandingPageSerializer(page).data,
            **public_collections,
        },
    }


def build_summary(previous, current):
    """Human-readable diff between two snapshots, e.g. '3 features updated'."""
    if not previous:
        return "Initial publish"
    lines = []

    prev_site = previous.get("site", {}) or {}
    curr_site = current.get("site", {}) or {}
    for label, keys in SITE_GROUPS.items():
        if any(k in prev_site and k in curr_site and prev_site.get(k) != curr_site.get(k) for k in keys):
            lines.append(label)

    prev_landing = previous.get("landing", {}) or {}
    curr_landing = current.get("landing", {}) or {}
    for label, keys in LANDING_AREAS:
        if any(
            k in prev_landing and k in curr_landing and prev_landing.get(k) != curr_landing.get(k)
            for k in keys
        ):
            lines.append(label)

    prev_colls = previous.get("collections", {}) or {}
    curr_colls = current.get("collections", {}) or {}
    for key, (_, _, _) in COLLECTIONS.items():
        before = {row["id"]: row for row in prev_colls.get(key, [])}
        after = {row["id"]: row for row in curr_colls.get(key, [])}
        created = len(set(after) - set(before))
        removed = len(set(before) - set(after))
        changed = sum(
            1
            for row_id in set(before) & set(after)
            if before[row_id] != after[row_id]
        )
        noun = COLLECTION_LABELS[key]
        plural = COLLECTION_PLURALS[key]
        if created:
            lines.append(f"{created} {noun if created == 1 else plural} added")
        if removed:
            lines.append(f"{removed} {noun if removed == 1 else plural} removed")
        if changed:
            lines.append(f"{changed} {noun if changed == 1 else plural} updated")

    if not lines:
        lines.append("Re-published without visible changes")
    if len(lines) > 8:
        lines = lines[:8] + ["More changes…"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Publish / unpublish
# ---------------------------------------------------------------------------


@transaction.atomic
def publish(user=None):
    """Atomically promote the current draft to a new published snapshot."""
    settings = SiteSettings.objects.load()
    page = LandingPage.objects.load()
    previous = CmsVersion.objects.filter(is_current=True).first()
    snapshot = build_snapshot()
    latest = CmsVersion.objects.order_by("-number").first()
    number = (latest.number if latest else 0) + 1
    version = CmsVersion.objects.create(
        number=number,
        published_by=user if user and user.is_authenticated else None,
        summary=build_summary(previous.snapshot if previous else None, snapshot),
        snapshot=snapshot,
        is_current=True,
    )
    CmsVersion.objects.filter(is_current=True).exclude(pk=version.pk).update(is_current=False)
    settings.is_published = True
    settings.save(update_fields=["is_published", "updated_at"])
    page.is_published = True
    page.save(update_fields=["is_published", "updated_at"])
    log(CmsActivity.Action.PUBLISHED, "Landing page", user, {"version": version.number})
    return version


@transaction.atomic
def unpublish(user=None):
    """Hide the public site, keeping published history for later restore."""
    settings = SiteSettings.objects.load()
    page = LandingPage.objects.load()
    settings.is_published = False
    settings.save(update_fields=["is_published", "updated_at"])
    page.is_published = False
    page.save(update_fields=["is_published", "updated_at"])
    CmsVersion.objects.filter(is_current=True).update(is_current=False)
    log(CmsActivity.Action.UNPUBLISHED, "Landing page", user)
    return True


# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------


def _apply_singleton(obj, data):
    applied = False
    for key, value in (data or {}).items():
        if key in SINGLETON_KEYS or not hasattr(obj, key):
            continue
        setattr(obj, key, value)
        applied = True
    if applied:
        obj.save()


def _apply_collection(model, rows):
    existing = {row.id: row for row in model.objects.all()}
    for row in rows or []:
        data = {key: value for key, value in row.items() if key != "id"}
        row_id = row.get("id")
        if row_id in existing:
            obj = existing.pop(row_id)
            for key, value in data.items():
                setattr(obj, key, value)
            obj.save()
        else:
            model.objects.create(**data)
    for obj in existing.values():
        obj.delete()


@transaction.atomic
def restore(version, user=None):
    """Copy a published version back into the draft tables (no republish)."""
    snapshot = version.snapshot or {}
    settings = SiteSettings.objects.load()
    _apply_singleton(settings, snapshot.get("site"))
    page = LandingPage.objects.load()
    landing = dict(snapshot.get("landing") or {})
    sections = landing.pop("sections", None)
    _apply_singleton(page, landing)
    if isinstance(sections, list) and sections:
        page.sections = [
            {"key": item["key"], "enabled": bool(item.get("enabled", True))}
            for item in sections
            if isinstance(item, dict) and "key" in item
        ]
        page.save(update_fields=["sections", "updated_at"])
    for key, (model, _, _) in COLLECTIONS.items():
        _apply_collection(model, snapshot.get("collections", {}).get(key))
    log(
        CmsActivity.Action.RESTORED,
        f"Version v{version.number}",
        user,
        {"version": version.number},
    )
    return version


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def ensure_initial_version():
    """Create the first snapshot for already-published sites (one-time)."""
    if CmsVersion.objects.exists():
        return None
    page = LandingPage.objects.load()
    if not page.is_published:
        return None
    version = CmsVersion.objects.create(
        number=1,
        published_by=None,
        summary="Initial publish",
        snapshot=build_snapshot(),
        is_current=True,
    )
    return version