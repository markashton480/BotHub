from django.contrib import admin

from .models import AuditEvent, Message, Project, Tag, Task, TaskAssignment, Thread, UserProfile, Webhook


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "kind", "display_name", "created_at")
    list_filter = ("kind",)
    search_fields = ("user__username", "display_name")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_archived", "created_by", "created_at")
    search_fields = ("name",)
    list_filter = ("is_archived",)


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "parent", "status", "priority", "position")
    list_filter = ("status", "priority", "project")
    search_fields = ("title", "description")
    inlines = [TaskAssignmentInline]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "color", "created_at")
    search_fields = ("name", "slug")


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "project", "task", "created_at")
    list_filter = ("kind",)
    search_fields = ("title",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "author_role", "author_label", "created_at")
    search_fields = ("body", "author_label")


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = ("task", "assignee", "role", "created_at")
    list_filter = ("role",)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("verb", "actor", "created_at")
    search_fields = ("verb", "metadata")


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "url", "events")
