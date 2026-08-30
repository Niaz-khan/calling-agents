from django.contrib import admin

from .models import Agent, AgentDeployment


class AgentDeploymentInline(admin.TabularInline):
    model = AgentDeployment
    extra = 1
    readonly_fields = ("public_identifier",)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "organization", "is_active", "created_at")
    list_filter = ("is_active", "organization")
    search_fields = ("name",)
    inlines = [AgentDeploymentInline]


@admin.register(AgentDeployment)
class AgentDeploymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "channel",
        "agent",
        "organization",
        "enabled",
        "public_identifier",
        "created_at",
    )
    list_filter = ("channel", "enabled", "organization")
    readonly_fields = ("public_identifier",)