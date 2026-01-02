from django import forms
from django.contrib import admin as django_admin
from django.contrib.admin import DateFieldListFilter
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import TokenProxy
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.mixins import BaseModelAdminMixin

from bothub.admin_site import bot_admin_site
from .models import AuditEvent, Message, Project, ProjectMembership, Tag, Task, TaskAssignment, Thread, UserProfile, Webhook

User = get_user_model()


class CreatedByAdminMixin:
    def save_model(self, request, obj, form, change):
        if hasattr(obj, "created_by") and not getattr(obj, "created_by_id", None):
            obj.created_by = request.user
        if hasattr(obj, "added_by") and not getattr(obj, "added_by_id", None):
            obj.added_by = request.user
        if hasattr(obj, "actor") and not getattr(obj, "actor_id", None):
            obj.actor = request.user
        super().save_model(request, obj, form, change)


class UserProfileInline(StackedInline):
    model = UserProfile
    extra = 0
    can_delete = False
    fields = ("kind", "display_name", "notes")


@django_admin.register(User, site=bot_admin_site)
class UserAdmin(BaseModelAdminMixin, BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ("username", "email", "is_staff", "is_active", "last_login")
    search_fields = ("username", "email")
    ordering = ("username",)


@django_admin.register(Group, site=bot_admin_site)
class GroupAdmin(BaseModelAdminMixin, BaseGroupAdmin):
    pass


@django_admin.register(UserProfile, site=bot_admin_site)
class UserProfileAdmin(ModelAdmin):
    list_display = ("user", "kind", "display_name", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__username", "display_name")
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


class ThreadInlineForProject(TabularInline):
    model = Thread
    fk_name = "project"
    extra = 0
    fields = ("title", "kind", "created_at")
    readonly_fields = ("created_at",)
    show_change_link = True


class TaskInlineForProject(TabularInline):
    model = Task
    fk_name = "project"
    extra = 0
    fields = ("title", "status", "priority", "position", "due_at")
    show_change_link = True


@django_admin.register(Project, site=bot_admin_site)
class ProjectAdmin(CreatedByAdminMixin, ModelAdmin):
    list_display = ("name", "is_archived", "created_by", "created_at")
    list_editable = ("is_archived",)
    search_fields = ("name",)
    list_filter = ("is_archived", ("created_at", DateFieldListFilter))
    ordering = ("name",)
    date_hierarchy = "created_at"
    inlines = [TaskInlineForProject, ThreadInlineForProject]
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


@django_admin.register(ProjectMembership, site=bot_admin_site)
class ProjectMembershipAdmin(ModelAdmin):
    list_display = ("project", "user", "role", "invited_by", "created_at")
    list_filter = ("role",)
    search_fields = ("project__name", "user__username")


class TaskAssignmentInline(TabularInline):
    model = TaskAssignment
    extra = 0
    autocomplete_fields = ("assignee", "added_by")


@django_admin.register(Task, site=bot_admin_site)
class TaskAdmin(CreatedByAdminMixin, ModelAdmin):
    list_display = ("title", "project", "parent", "status", "priority", "due_at", "position")
    list_editable = ("status", "priority", "due_at", "position")
    list_filter = ("status", "priority", "project", ("created_at", DateFieldListFilter))
    search_fields = ("title", "description")
    list_select_related = ("project", "parent", "created_by")
    inlines = [TaskAssignmentInline]
    autocomplete_fields = ("project", "parent", "created_by", "tags")
    date_hierarchy = "created_at"
    fieldsets = (
        ("Plan", {"fields": ("project", "parent", "title", "description")}),
        ("Status", {"fields": ("status", "priority", "position", "due_at", "tags")}),
        ("Audit", {"fields": ("created_by",)}),
    )
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


@django_admin.register(Tag, site=bot_admin_site)
class TagAdmin(ModelAdmin):
    list_display = ("name", "slug", "color", "created_at")
    search_fields = ("name", "slug")
    ordering = ("name",)
    date_hierarchy = "created_at"
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }


class MessageInline(StackedInline):
    model = Message
    extra = 0
    autocomplete_fields = ("created_by",)
    fields = ("author_role", "author_label", "body", "metadata", "created_by", "created_at")
    readonly_fields = ("created_at",)


@django_admin.register(Thread, site=bot_admin_site)
class ThreadAdmin(CreatedByAdminMixin, ModelAdmin):
    list_display = ("title", "kind", "project", "task", "created_by", "created_at")
    list_filter = ("kind",)
    search_fields = ("title", "project__name", "task__title")
    list_select_related = ("project", "task", "created_by")
    autocomplete_fields = ("project", "task", "created_by")
    date_hierarchy = "created_at"
    inlines = [MessageInline]
    fieldsets = (
        ("Thread", {"fields": ("title", "kind")}),
        ("Scope", {"fields": ("project", "task")}),
        ("Audit", {"fields": ("created_by",)}),
    )


@django_admin.register(Message, site=bot_admin_site)
class MessageAdmin(CreatedByAdminMixin, ModelAdmin):
    list_display = ("thread", "author_role", "author_label", "created_by", "created_at")
    list_filter = ("author_role",)
    search_fields = ("body", "author_label", "thread__title")
    list_select_related = ("thread", "created_by")
    autocomplete_fields = ("thread", "created_by")
    date_hierarchy = "created_at"
    fieldsets = (
        ("Message", {"fields": ("thread", "body")}),
        ("Author", {"fields": ("author_role", "author_label", "created_by")}),
        ("Metadata", {"fields": ("metadata",), "classes": ("collapse",)}),
    )
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 6})},
        models.JSONField: {"widget": JSONEditorWidget(height="320px")},
    }


@django_admin.register(TaskAssignment, site=bot_admin_site)
class TaskAssignmentAdmin(CreatedByAdminMixin, ModelAdmin):
    list_display = ("task", "assignee", "role", "added_by", "created_at")
    list_filter = ("role",)
    search_fields = ("task__title", "assignee__username")
    list_select_related = ("task", "assignee", "added_by")
    autocomplete_fields = ("task", "assignee", "added_by")
    date_hierarchy = "created_at"


@django_admin.register(AuditEvent, site=bot_admin_site)
class AuditEventAdmin(ModelAdmin):
    list_display = ("verb", "actor", "created_at")
    list_filter = ("verb",)
    search_fields = ("verb", "metadata", "actor__username")
    date_hierarchy = "created_at"
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget(height="320px")},
    }


@django_admin.register(Webhook, site=bot_admin_site)
class WebhookAdmin(ModelAdmin):
    list_display = ("name", "url", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "url", "events")
    date_hierarchy = "created_at"
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget(height="280px")},
    }


class TokenProxyAdmin(BaseModelAdminMixin, TokenAdmin):
    pass


bot_admin_site.register(TokenProxy, TokenProxyAdmin)
