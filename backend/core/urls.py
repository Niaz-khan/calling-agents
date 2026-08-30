from django.urls import path

from . import views

urlpatterns = [
    path("", views.root),
    path("health", views.health),
    path("db-health", views.db_health),
]