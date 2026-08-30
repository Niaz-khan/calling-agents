from django.urls import path

from .views import (
    BaseDetailView,
    BaseDocumentsView,
    BaseListCreateView,
    DocumentDetailView,
    KnowledgeSearchView,
)

urlpatterns = [
    path("knowledge/bases", BaseListCreateView.as_view()),
    path("knowledge/bases/<int:knowledge_base_id>", BaseDetailView.as_view()),
    path(
        "knowledge/bases/<int:knowledge_base_id>/documents",
        BaseDocumentsView.as_view(),
    ),
    path("knowledge/documents/<int:document_id>", DocumentDetailView.as_view()),
    path("knowledge/search", KnowledgeSearchView.as_view()),
]