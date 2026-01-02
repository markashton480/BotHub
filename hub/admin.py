from django.contrib import admin

from bothub.admin_site import bot_admin_site
from .models import AuditEvent, Message, Project, Tag, Task, TaskAssignment, Thread, UserProfile, Webhook


@admin.register(UserProfile, site=bot_admin_site)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "display_name", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__username", "display_name")


@admin.register(Project, site=bot_admin_site)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "created_by", "created_at")
    search_fields = ("name",)
    list_filter = ("is_archived",)


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 0


@admin.register(Task, site=bot_admin_site)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "parent", "status", "priority", "position")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description")
    inlines = [TaskAssignmentInline]


@admin.register(Tag, site=bot_admin_site)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "created_at")
    search_fields = ("name", "slug")


@admin.register(Thread, site=bot_admin_site)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "project", "task", "created_at")
    list_filter = ("kind",)
    search_fields = ("title",)


@admin.register(Message, site=bot_admin_site)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "author_role", "author_label", "created_at")
    search_fields = ("body", "author_label")


@admin.register(TaskAssignment, site=bot_admin_site)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("task", "assignee", "role", "created_at")
    list_filter = ("role",)


@admin.register(AuditEvent, site=bot_admin_site)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("verb", "actor", "created_at")
    search_fields = ("verb", "metadata")


@admin.register(Webhook, site=bot_admin_site)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "url", "events")
