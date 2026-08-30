"""Seed default CMS content so a fresh database has a published landing page.

Idempotent: only fills rows that do not exist, so edits made after this
migration are never overwritten. It uses *historical* models so later schema
changes (e.g. new SiteSettings columns) never break data seeding.
"""

from django.db import migrations

from apps.cms.seed import (
    DEFAULT_FAQS,
    DEFAULT_FEATURES,
    DEFAULT_FOOTER,
    DEFAULT_NAV,
    DEFAULT_PRICING,
    DEFAULT_PROBLEM_ITEMS,
    DEFAULT_SECTIONS,
    DEFAULT_STEPS,
    DEFAULT_TESTIMONIALS,
    DEFAULT_USE_CASES,
    DEFAULT_VALUE_STRIP,
)


def _seed_list(model, items):
    if model.objects.exists():
        return
    model.objects.bulk_create(
        [model(**item, order=i) for i, item in enumerate(items)]
    )


def _apply(apps, schema_editor):
    SiteSettings = apps.get_model("cms", "SiteSettings")
    LandingPage = apps.get_model("cms", "LandingPage")
    FeatureSection = apps.get_model("cms", "FeatureSection")
    UseCase = apps.get_model("cms", "UseCase")
    Testimonial = apps.get_model("cms", "Testimonial")
    FAQ = apps.get_model("cms", "FAQ")
    NavigationItem = apps.get_model("cms", "NavigationItem")
    FooterSection = apps.get_model("cms", "FooterSection")
    PricingPlan = apps.get_model("cms", "PricingPlan")

    if not SiteSettings.objects.exists():
        SiteSettings.objects.create(pk=1)
    if not LandingPage.objects.exists():
        page = LandingPage.objects.create(pk=1)
        page.sections = DEFAULT_SECTIONS
        page.is_published = True
        page.value_strip_items = DEFAULT_VALUE_STRIP
        page.problem_items = DEFAULT_PROBLEM_ITEMS
        page.how_works_steps = DEFAULT_STEPS
        page.save()

    _seed_list(FeatureSection, DEFAULT_FEATURES)
    _seed_list(UseCase, DEFAULT_USE_CASES)
    _seed_list(Testimonial, DEFAULT_TESTIMONIALS)
    _seed_list(FAQ, DEFAULT_FAQS)
    _seed_list(NavigationItem, DEFAULT_NAV)
    _seed_list(FooterSection, DEFAULT_FOOTER)
    _seed_list(PricingPlan, DEFAULT_PRICING)


def _rollback(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(_apply, _rollback),
    ]