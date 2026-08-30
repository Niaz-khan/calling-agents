from django.contrib import admin

from .models import Conversation, ConversationMessage, PhoneCall


class ConversationMessageInline(admin.TabularInline):
    model = ConversationMessage
    extra = 0
    readonly_fields = ("role", "content", "tool_call_id", "created_at")


class PhoneCallInline(admin.StackedInline):
    model = PhoneCall
    can_delete = False
    extra = 0


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "status", "agent", "organization", "outcome", "started_at", "ended_at")
    list_filter = ("channel", "status", "outcome", "organization")
    inlines = [PhoneCallInline, ConversationMessageInline]


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "content", "tool_call_id", "created_at")
    list_filter = ("role",)


@admin.register(PhoneCall)
class PhoneCallAdmin(admin.ModelAdmin):
    list_display = ("conversation", "direction", "provider_status", "caller_number", "provider_call_id", "recording_url")
    list_filter = ("direction", "provider_status")