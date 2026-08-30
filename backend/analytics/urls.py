from django.urls import path

from .views import AnalyticsOverviewView

urlpatterns = [
    path("analytics/overview", AnalyticsOverviewView.as_view()),
]