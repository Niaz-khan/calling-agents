from rest_framework import serializers

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


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "id",
            "is_published",
            "site_name",
            "logo",
            "favicon",
            "website_url",
            "font_family",
            "primary_color",
            "secondary_color",
            "contact_email",
            "support_email",
            "social_links",
            "announcement_enabled",
            "announcement_text",
            "meta_title",
            "meta_description",
            "og_title",
            "og_description",
            "og_image",
            "canonical_url",
            "robots",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class LandingPageSerializer(serializers.ModelSerializer):
    sections = serializers.SerializerMethodField()

    class Meta:
        model = LandingPage
        fields = [
            "id",
            "is_published",
            "sections",
            "hero_enabled",
            "hero_badge",
            "hero_title",
            "hero_subtitle",
            "hero_primary_cta",
            "hero_secondary_cta",
            "value_strip_title",
            "value_strip_items",
            "problem_title",
            "problem_items",
            "solution_title",
            "solution_text",
            "features_title",
            "features_subtitle",
            "showcase_title",
            "showcase_subtitle",
            "how_works_title",
            "how_works_steps",
            "website_section_title",
            "website_section_text",
            "website_section_cta",
            "phone_section_title",
            "phone_section_text",
            "phone_section_cta",
            "api_section_title",
            "api_section_text",
            "api_section_cta",
            "use_cases_title",
            "use_cases_subtitle",
            "analytics_title",
            "analytics_subtitle",
            "pricing_title",
            "pricing_subtitle",
            "pricing_disclaimer",
            "faq_title",
            "faq_subtitle",
            "cta_title",
            "cta_subtitle",
            "cta_primary",
            "cta_secondary",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_sections(self, obj):
        return obj.sections_for()


class OrderedSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "order", "enabled"]
        read_only_fields = ["id"]


class FeatureSectionSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = FeatureSection
        fields = OrderedSerializer.Meta.fields + ["title", "description", "icon"]


class UseCaseSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = UseCase
        fields = OrderedSerializer.Meta.fields + ["title", "description", "icon"]


class TestimonialSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = Testimonial
        fields = OrderedSerializer.Meta.fields + [
            "name",
            "company",
            "role",
            "quote",
            "avatar",
        ]


class PricingPlanSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = PricingPlan
        fields = OrderedSerializer.Meta.fields + [
            "name",
            "description",
            "price",
            "billing_period",
            "features",
            "cta_text",
            "highlighted",
        ]


class FAQSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = FAQ
        fields = OrderedSerializer.Meta.fields + ["question", "answer"]


class NavigationItemSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = NavigationItem
        fields = OrderedSerializer.Meta.fields + ["label", "url"]


class FooterSectionSerializer(OrderedSerializer):
    class Meta(OrderedSerializer.Meta):
        model = FooterSection
        fields = OrderedSerializer.Meta.fields + ["title", "links"]


# Public-facing serializers: a strict subset, enabled-only rows only.
class PublicListSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ["id", "order", "enabled"]


class PublicFeatureSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = FeatureSection
        fields = PublicListSerializer.Meta.fields + ["title", "description", "icon"]


class PublicUseCaseSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = UseCase
        fields = PublicListSerializer.Meta.fields + ["title", "description", "icon"]


class PublicTestimonialSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = Testimonial
        fields = PublicListSerializer.Meta.fields + [
            "name",
            "company",
            "role",
            "quote",
            "avatar",
        ]


class PublicPricingPlanSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = PricingPlan
        fields = PublicListSerializer.Meta.fields + [
            "name",
            "description",
            "price",
            "billing_period",
            "features",
            "cta_text",
            "highlighted",
        ]


class PublicFAQSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = FAQ
        fields = PublicListSerializer.Meta.fields + ["question", "answer"]


class PublicNavigationItemSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = NavigationItem
        fields = PublicListSerializer.Meta.fields + ["label", "url"]


class PublicFooterSectionSerializer(PublicListSerializer):
    class Meta(PublicListSerializer.Meta):
        model = FooterSection
        fields = PublicListSerializer.Meta.fields + ["title", "links"]


class PublicSiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "site_name",
            "logo",
            "favicon",
            "website_url",
            "font_family",
            "primary_color",
            "secondary_color",
            "social_links",
            "announcement_enabled",
            "announcement_text",
            "meta_title",
            "meta_description",
            "og_title",
            "og_description",
            "og_image",
            "canonical_url",
            "robots",
        ]


class PublicLandingPageSerializer(serializers.ModelSerializer):
    sections = serializers.SerializerMethodField()

    class Meta:
        model = LandingPage
        fields = [
            "sections",
            "hero_enabled",
            "hero_badge",
            "hero_title",
            "hero_subtitle",
            "hero_primary_cta",
            "hero_secondary_cta",
            "value_strip_title",
            "value_strip_items",
            "problem_title",
            "problem_items",
            "solution_title",
            "solution_text",
            "features_title",
            "features_subtitle",
            "showcase_title",
            "showcase_subtitle",
            "how_works_title",
            "how_works_steps",
            "website_section_title",
            "website_section_text",
            "website_section_cta",
            "phone_section_title",
            "phone_section_text",
            "phone_section_cta",
            "api_section_title",
            "api_section_text",
            "api_section_cta",
            "use_cases_title",
            "use_cases_subtitle",
            "analytics_title",
            "analytics_subtitle",
            "pricing_title",
            "pricing_subtitle",
            "pricing_disclaimer",
            "faq_title",
            "faq_subtitle",
            "cta_title",
            "cta_subtitle",
            "cta_primary",
            "cta_secondary",
        ]

    def get_sections(self, obj):
        return obj.sections_for()


def enabled_rows(model, serializer):
    return serializer(model.objects.filter(enabled=True), many=True).data


class CmsVersionSerializer(serializers.ModelSerializer):
    published_by = serializers.SerializerMethodField()

    class Meta:
        model = CmsVersion
        fields = ["id", "number", "published_at", "published_by", "summary", "is_current"]
        read_only_fields = fields

    def get_published_by(self, obj):
        return obj.published_by.email if obj.published_by else "Seed"


class CmsActivitySerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    action = serializers.CharField(source="get_action_display")

    class Meta:
        model = CmsActivity
        fields = ["id", "actor", "action", "resource", "detail", "created_at"]
        read_only_fields = fields

    def get_actor(self, obj):
        return obj.actor.email if obj.actor else None