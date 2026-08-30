from django.urls import path

from . import views_admin, views_public

urlpatterns = [
    # Public read-only CMS (GET only, AllowAny, throttled).
    path("public/site-config", views_public.SiteConfigView.as_view()),
    path("public/landing-page", views_public.LandingPageView.as_view()),
    path("public/features", views_public.FeatureListView.as_view()),
    path("public/use-cases", views_public.UseCaseListView.as_view()),
    path("public/testimonials", views_public.TestimonialListView.as_view()),
    path("public/pricing", views_public.PricingPlanListView.as_view()),
    path("public/faqs", views_public.FAQListView.as_view()),
    path("public/navigation", views_public.NavigationItemListView.as_view()),
    path("public/footer", views_public.FooterSectionListView.as_view()),
    # Platform-admin CMS CRUD (IsContentAdmin).
    path("platform/cms/site-settings", views_admin.SiteSettingsAdminView.as_view()),
    path("platform/cms/landing", views_admin.LandingPageAdminView.as_view()),
    path("platform/cms/landing/publish", views_admin.LandingPagePublishView.as_view()),
    # Platform-admin publishing workflow.
    path("platform/cms/publish", views_admin.CmsPublishView.as_view()),
    path("platform/cms/publish/preview", views_admin.CmsPublishPreviewView.as_view()),
    path("platform/cms/unpublish", views_admin.CmsUnpublishView.as_view()),
    path("platform/cms/versions", views_admin.CmsVersionsView.as_view()),
    path(
        "platform/cms/restore/<int:version_number>",
        views_admin.CmsRestoreView.as_view(),
    ),
    path("platform/cms/activity", views_admin.CmsActivityView.as_view()),
]

_ordered_views = [
    ("platform/cms/features", views_admin.FeatureSectionViewSet),
    ("platform/cms/use-cases", views_admin.UseCaseViewSet),
    ("platform/cms/testimonials", views_admin.TestimonialViewSet),
    ("platform/cms/pricing", views_admin.PricingPlanViewSet),
    ("platform/cms/faqs", views_admin.FAQViewSet),
    ("platform/cms/navigation", views_admin.NavigationItemViewSet),
    ("platform/cms/footer", views_admin.FooterSectionViewSet),
]

for prefix, viewset in _ordered_views:
    urlpatterns += [
        path(prefix, viewset.as_view({"get": "list", "post": "create"})),
        path(
            f"{prefix}/<int:pk>",
            viewset.as_view(
                {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
            ),
        ),
    ]