from django.contrib import admin

from .models import KnowledgeBase, KnowledgeChunk, KnowledgeDocument


@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "agent", "organization", "created_at")
    list_filter = ("organization",)


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "filename", "knowledge_base", "source_type", "status", "created_at")
    list_filter = ("source_type", "status")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "document", "chunk_index", "token_count", "created_at")