from django.urls import path

from .views import BusinessConfigView

urlpatterns = [
    path("business-config", BusinessConfigView.as_view()),
]