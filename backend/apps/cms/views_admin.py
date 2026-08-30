"""Platform-admin CMS CRUD + publishing workflow.

Every mutation endpoint here requires a platform content role
(SUPER_ADMIN / PLATFORM_ADMIN / CONTENT_ADMIN). Business users -- even owners
of their own organization -- are rejected with 403.

Publishing actions (publish, unpublish, restore) additionally require
PLATFORM_ADMIN / SUPER_ADMIN; CONTENT_ADMIN may edit drafts and view history
but cannot publish.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.platform.permissions import IsContentAdmin, IsPlatformAdmin

from . import publishing
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
    CmsActivitySerializer,
    CmsVersionSerializer,
    FAQSerializer,
    FeatureSectionSerializer,
    FooterSectionSerializer,
    LandingPageSerializer,
    NavigationItemSerializer,
    PricingPlanSerializer,
    SiteSettingsSerializer,
    TestimonialSerializer,
    UseCaseSerializer,
)

CMS_PERMISSION = [IsContentAdmin]
PUBLISH_PERMISSION = [IsPlatformAdmin]


class _SingletonView(APIView):
    permission_classes = CMS_PERMISSION
    model = None
    serializer_class = None
    partial = False
    resource_label = "Content"

    def get_object(self):
        return self.model.objects.load()

    def get(self, request):
        return Response(self.serializer_class(self.get_object()).data)

    def put(self, request):
        obj = self.get_object()
        serializer = self.serializer_class(obj, data=request.data, partial=self.partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        if "sections" in request.data and self.model is LandingPage:
            publishing.log(
                CmsActivity.Action.SECTIONS_UPDATED, self.resource_label, request.user
            )
        else:
            publishing.log(CmsActivity.Action.DRAFT_SAVED, self.resource_label, request.user)
        return Response(serializer.data)


class SiteSettingsAdminView(_SingletonView):
    model = SiteSettings
    serializer_class = SiteSettingsSerializer
    partial = True
    resource_label = "Site settings"


class LandingPageAdminView(_SingletonView):
    model = LandingPage
    serializer_class = LandingPageSerializer
    partial = True
    resource_label = "Landing page"


class LandingPagePublishView(APIView):
    """Backward-compatible publish toggle backed by the workflow service."""

    permission_classes = CMS_PERMISSION

    def post(self, request):
        published = request.data.get("is_published", True)
        if not isinstance(published, bool):
            return Response(
                {"detail": "is_published must be a boolean"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if published:
            version = publishing.publish(request.user)
            return Response(
                {
                    "is_published": True,
                    "version": version.number,
                    "summary": version.summary,
                }
            )
        publishing.unpublish(request.user)
        return Response({"is_published": False})


class CmsPublishView(APIView):
    permission_classes = PUBLISH_PERMISSION

    def post(self, request):
        version = publishing.publish(request.user)
        return Response(
            {
                "is_published": True,
                "version": version.number,
                "published_at": version.published_at,
                "summary": version.summary,
            },
            status=status.HTTP_201_CREATED,
        )


class CmsPublishPreviewView(APIView):
    """Dry-run summary of what publishing the current draft would change."""

    permission_classes = PUBLISH_PERMISSION

    def get(self, request):
        previous = CmsVersion.objects.filter(is_current=True).first()
        snapshot = publishing.build_snapshot()
        summary = publishing.build_summary(
            previous.snapshot if previous else None, snapshot
        )
        return Response({"summary": summary.split("\n")})


class CmsUnpublishView(APIView):
    permission_classes = PUBLISH_PERMISSION

    def post(self, request):
        publishing.unpublish(request.user)
        return Response({"is_published": False})


class CmsVersionsView(APIView):
    permission_classes = CMS_PERMISSION

    def get(self, request):
        versions = CmsVersionSerializer(CmsVersion.objects.all(), many=True).data
        return Response(versions)


class CmsRestoreView(APIView):
    permission_classes = PUBLISH_PERMISSION

    def post(self, request, version_number):
        version = get_object_or_404(CmsVersion, number=version_number)
        publishing.restore(version, request.user)
        return Response(
            {
                "restored": True,
                "version": version.number,
                "detail": f"Version v{version.number} restored as a draft. Publish it to go live.",
            }
        )


class CmsActivityView(APIView):
    permission_classes = CMS_PERMISSION

    def get(self, request):
        activities = CmsActivitySerializer(
            CmsActivity.objects.all()[:50], many=True
        ).data
        return Response(activities)


class _OrderedModelViewSet(ModelViewSet):
    permission_classes = CMS_PERMISSION
    queryset = None
    serializer_class = None
    resource_label = "Content"

    def get_queryset(self):
        return self.queryset.model.objects.all()

    def perform_create(self, serializer):
        obj = serializer.save()
        publishing.log(
            CmsActivity.Action.CREATED, f"{self.resource_label} #{obj.id}", self.request.user
        )

    def perform_update(self, serializer):
        obj = serializer.save()
        publishing.log(
            CmsActivity.Action.UPDATED, f"{self.resource_label} #{obj.id}", self.request.user
        )

    def perform_destroy(self, instance):
        publishing.log(
            CmsActivity.Action.DELETED, f"{self.resource_label} #{instance.id}", self.request.user
        )
        instance.delete()


class FeatureSectionViewSet(_OrderedModelViewSet):
    queryset = FeatureSection.objects.all()
    serializer_class = FeatureSectionSerializer
    resource_label = "Feature"


class UseCaseViewSet(_OrderedModelViewSet):
    queryset = UseCase.objects.all()
    serializer_class = UseCaseSerializer
    resource_label = "Use case"


class TestimonialViewSet(_OrderedModelViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    resource_label = "Testimonial"


class PricingPlanViewSet(_OrderedModelViewSet):
    queryset = PricingPlan.objects.all()
    serializer_class = PricingPlanSerializer
    resource_label = "Pricing plan"


class FAQViewSet(_OrderedModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    resource_label = "FAQ"


class NavigationItemViewSet(_OrderedModelViewSet):
    queryset = NavigationItem.objects.all()
    serializer_class = NavigationItemSerializer
    resource_label = "Nav item"


class FooterSectionViewSet(_OrderedModelViewSet):
    queryset = FooterSection.objects.all()
    serializer_class = FooterSectionSerializer
    resource_label = "Footer section"