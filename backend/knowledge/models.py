from django.db import models


class KnowledgeBase(models.Model):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="knowledge_bases"
    )
    agent = models.OneToOneField(
        "agents.Agent", on_delete=models.CASCADE, related_name="knowledge_base"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class KnowledgeDocument(models.Model):
    knowledge_base = models.ForeignKey(
        KnowledgeBase, on_delete=models.CASCADE, related_name="documents"
    )
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    source_type = models.CharField(max_length=50)
    title = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50)
    error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk_index = models.IntegerField()
    content = models.TextField()
    embedding = models.JSONField()
    token_count = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="uq_chunk_document_index"
            )
        ]
        ordering = ["chunk_index"]

    def __str__(self):
        return f"{self.document_id} chunk {self.chunk_index}"