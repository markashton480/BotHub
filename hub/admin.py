from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db import models

from bothub.admin_site import bot_admin_site
from .models import AuditEvent, Message, Project, Tag, Task, TaskAssignment, Thread, UserProfile, Webhook

User = get_user_model()


@admin.register(User, site=bot_admin_site)
class UserAdmin(BaseUserAdmin):
    pass


@admin.register(UserProfile, site=bot_admin_site)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "display_name", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__username", "display_name")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


@admin.register(Project, site=bot_admin_site)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "created_by", "created_at")
    search_fields = ("name",)
    list_filter = ("is_archived",)
    ordering = ("name",)
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 0


@admin.register(Task, site=bot_admin_site)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "parent", "status", "priority", "position")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description")
    inlines = [TaskAssignmentInline]
    autocomplete_fields = ("project", "parent", "created_by", "tags")
    fieldsets = (
        ("Plan", {"fields": ("project", "parent", "title", "description")}),
        ("Status", {"fields": ("status", "priority", "position", "due_at", "tags")}),
        ("Audit", {"fields": ("created_by",)}),
    )
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


@admin.register(Tag, site=bot_admin_site)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "created_at")
    search_fields = ("name", "slug")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


@admin.register(Thread, site=bot_admin_site)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "project", "task", "created_at")
    list_filter = ("kind",)
    search_fields = ("title",)
    autocomplete_fields = ("project", "task", "created_by")
    fieldsets = (
        ("Thread", {"fields": ("title", "kind")}),
        ("Scope", {"fields": ("project", "task")}),
        ("Audit", {"fields": ("created_by",)}),
    )


@admin.register(Message, site=bot_admin_site)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "author_role", "author_label", "created_at")
    search_fields = ("body", "author_label")
    autocomplete_fields = ("thread", "created_by")
    fieldsets = (
        ("Message", {"fields": ("thread", "body")}),
        ("Author", {"fields": ("author_role", "author_label", "created_by")}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
    )
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 6})},
        models.JSONField: {"widget": forms.Textarea(attrs={"rows": 6, "class": "monospace"})},
    }


@admin.register(TaskAssignment, site=bot_admin_site)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("task", "assignee", "role", "created_at")
    list_filter = ("role",)


@admin.register(AuditEvent, site=bot_admin_site)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("verb", "actor", "created_at")
    search_fields = ("verb", "metadata")
    formfield_overrides = {
        models.JSONField: {"widget": forms.Textarea(attrs={"rows": 6, "class": "monospace"})},
    }


@admin.register(Webhook, site=bot_admin_site)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "url", "events")
    formfield_overrides = {
        models.JSONField: {"widget": forms.Textarea(attrs={"rows": 4, "class": "monospace"})},
    }
