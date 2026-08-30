from rest_framework import serializers

from .models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    agent_id = serializers.IntegerField()

    class Meta:
        model = KnowledgeBase
        fields = ["id", "agent_id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    knowledge_base_id = serializers.IntegerField(source="knowledge_base.pk", read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = [
            "id",
            "knowledge_base_id",
            "filename",
            "content_type",
            "source_type",
            "title",
            "status",
            "error",
            "created_at",
        ]
        read_only_fields = fields


class KnowledgeChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeChunk
        fields = ["id", "chunk_index", "content"]


class KnowledgeDocumentDetailSerializer(KnowledgeDocumentSerializer):
    chunks = serializers.SerializerMethodField()

    class Meta(KnowledgeDocumentSerializer.Meta):
        fields = KnowledgeDocumentSerializer.Meta.fields + ["chunks"]

    def get_chunks(self, obj):
        return KnowledgeChunkSerializer(
            obj.chunks.all().order_by("chunk_index"), many=True
        ).data


class KnowledgeSearchRequestSerializer(serializers.Serializer):
    agent_id = serializers.IntegerField()
    query = serializers.CharField(min_length=1)
    limit = serializers.IntegerField(min_value=1, max_value=20, required=False)
    threshold = serializers.FloatField(
        min_value=0.0, max_value=1.0, required=False
    )