from django.contrib import admin

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


class OrderedAdmin(admin.ModelAdmin):
    list_display = ("id", "__str__", "enabled", "order")
    list_editable = ("enabled", "order")
    list_filter = ("enabled",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "site_name", "is_published", "updated_at")


@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    list_display = ("id", "hero_title", "is_published", "updated_at")
    list_filter = ("is_published",)


@admin.register(FeatureSection)
class FeatureSectionAdmin(OrderedAdmin):
    list_display = ("id", "title", "icon", "enabled", "order")


@admin.register(UseCase)
class UseCaseAdmin(OrderedAdmin):
    list_display = ("id", "title", "icon", "enabled", "order")


@admin.register(Testimonial)
class TestimonialAdmin(OrderedAdmin):
    list_display = ("id", "name", "company", "enabled", "order")


@admin.register(PricingPlan)
class PricingPlanAdmin(OrderedAdmin):
    list_display = ("id", "name", "price", "highlighted", "enabled", "order")


@admin.register(FAQ)
class FAQAdmin(OrderedAdmin):
    list_display = ("id", "question", "enabled", "order")


@admin.register(NavigationItem)
class NavigationItemAdmin(OrderedAdmin):
    list_display = ("id", "label", "url", "enabled", "order")


@admin.register(FooterSection)
class FooterSectionAdmin(OrderedAdmin):
    list_display = ("id", "title", "enabled", "order")


@admin.register(CmsVersion)
class CmsVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "published_by", "is_current", "published_at")
    list_filter = ("is_current",)


@admin.register(CmsActivity)
class CmsActivityAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "action", "resource", "created_at")
    list_filter = ("action",)