"""Public, read-only CMS endpoints.

Only published/enabled content is ever exposed. All views are GET-only,
``AllowAny``, and throttled to keep public reads cheap.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import (
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
    PublicFAQSerializer,
    PublicFeatureSerializer,
    PublicFooterSectionSerializer,
    PublicLandingPageSerializer,
    PublicNavigationItemSerializer,
    PublicPricingPlanSerializer,
    PublicSiteSettingsSerializer,
    PublicTestimonialSerializer,
    PublicUseCaseSerializer,
)


class PublicCMSView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_cms"


def current_snapshot():
    version = CmsVersion.objects.filter(is_current=True).first()
    if version:
        return version.snapshot.get("public") or {}
    return None


def enabled_or_404(model, serializer_class):
    rows = model.objects.filter(enabled=True)
    return serializer_class(rows, many=True).data


def published_or_live(collection_key, model, serializer_class):
    public = current_snapshot()
    if public is not None:
        return public.get(collection_key, [])
    return enabled_or_404(model, serializer_class)


class SiteConfigView(PublicCMSView):
    def get(self, request):
        settings = SiteSettings.objects.load()
        if not settings.is_published:
            return Response(
                {"detail": "Site configuration not available"},
                status=status.HTTP_404_NOT_FOUND,
            )
        public = current_snapshot()
        if public is not None:
            return Response(public.get("site") or PublicSiteSettingsSerializer(settings).data)
        return Response(PublicSiteSettingsSerializer(settings).data)


class LandingPageView(PublicCMSView):
    def get(self, request):
        page = LandingPage.objects.load()
        if not page.is_published:
            return Response(
                {"detail": "Landing page not published"},
                status=status.HTTP_404_NOT_FOUND,
            )
        public = current_snapshot()
        if public is not None:
            return Response(public.get("landing") or PublicLandingPageSerializer(page).data)
        return Response(PublicLandingPageSerializer(page).data)


class FeatureListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("features", FeatureSection, PublicFeatureSerializer))


class UseCaseListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("use_cases", UseCase, PublicUseCaseSerializer))


class TestimonialListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("testimonials", Testimonial, PublicTestimonialSerializer))


class PricingPlanListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("pricing", PricingPlan, PublicPricingPlanSerializer))


class FAQListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("faqs", FAQ, PublicFAQSerializer))


class NavigationItemListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("nav", NavigationItem, PublicNavigationItemSerializer))


class FooterSectionListView(PublicCMSView):
    def get(self, request):
        return Response(published_or_live("footer", FooterSection, PublicFooterSectionSerializer))