from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agents.models import Agent
from apps.tenancy.access import get_request_organization

from .models import KnowledgeBase, KnowledgeDocument
from .serializers import (
    KnowledgeBaseSerializer,
    KnowledgeDocumentDetailSerializer,
    KnowledgeDocumentSerializer,
    KnowledgeSearchRequestSerializer,
)
from .services import (
    create_knowledge_base,
    delete_document,
    delete_knowledge_base,
    get_owned_knowledge_base,
    ingest_document,
    list_documents,
    search_knowledge_base,
)


def _organization(request):
    organization = get_request_organization(request)
    if organization is None:
        raise NotFound("Organization not found")
    return organization


def _owned_base(organization, knowledge_base_id):
    knowledge_base = get_owned_knowledge_base(organization, knowledge_base_id)
    if knowledge_base is None:
        raise NotFound("Knowledge base not found")
    return knowledge_base


def _owned_agent(organization, agent_id):
    agent = Agent.objects.filter(id=agent_id, organization=organization).first()
    if agent is None:
        raise NotFound("Agent not found")
    return agent


class BaseListCreateView(APIView):
    def get(self, request):
        organization = _organization(request)
        bases = KnowledgeBase.objects.filter(organization=organization)
        return Response(KnowledgeBaseSerializer(bases, many=True).data)

    def post(self, request):
        organization = _organization(request)
        serializer = KnowledgeBaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        agent = _owned_agent(organization, data["agent_id"])
        knowledge_base = create_knowledge_base(
            organization,
            agent,
            name=data["name"],
            description=data.get("description"),
        )
        return Response(
            KnowledgeBaseSerializer(knowledge_base).data,
            status=status.HTTP_201_CREATED,
        )


class BaseDetailView(APIView):
    def get(self, request, knowledge_base_id):
        organization = _organization(request)
        knowledge_base = _owned_base(organization, knowledge_base_id)
        return Response(KnowledgeBaseSerializer(knowledge_base).data)

    def delete(self, request, knowledge_base_id):
        organization = _organization(request)
        knowledge_base = _owned_base(organization, knowledge_base_id)
        delete_knowledge_base(knowledge_base)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BaseDocumentsView(APIView):
    def get(self, request, knowledge_base_id):
        organization = _organization(request)
        knowledge_base = _owned_base(organization, knowledge_base_id)
        return Response(
            KnowledgeDocumentSerializer(list_documents(knowledge_base), many=True).data
        )

    def post(self, request, knowledge_base_id):
        organization = _organization(request)
        knowledge_base = _owned_base(organization, knowledge_base_id)
        file = request.FILES.get("file")
        if file is None:
            raise ValidationError("Uploaded file is required")
        content = file.read()
        if not content:
            raise ValidationError("Uploaded file is empty")
        document = ingest_document(
            organization,
            knowledge_base,
            filename=file.name or "document",
            content=content,
            content_type=file.content_type,
        )
        return Response(
            KnowledgeDocumentSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    def get(self, request, document_id):
        organization = _organization(request)
        document = _owned_document(organization, document_id)
        return Response(KnowledgeDocumentDetailSerializer(document).data)

    def delete(self, request, document_id):
        organization = _organization(request)
        document = _owned_document(organization, document_id)
        delete_document(document)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _owned_document(organization, document_id):
    document = (
        KnowledgeDocument.objects.filter(
            knowledge_base__organization=organization, id=document_id
        )
        .select_related("knowledge_base")
        .first()
    )
    if document is None:
        raise NotFound("Document not found")
    return document


class KnowledgeSearchView(APIView):
    def post(self, request):
        organization = _organization(request)
        serializer = KnowledgeSearchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _owned_agent(organization, data["agent_id"])
        result = search_knowledge_base(
            organization,
            agent_id=data["agent_id"],
            query=data["query"],
            limit=data.get("limit"),
            threshold=data.get("threshold"),
        )
        return Response(result)