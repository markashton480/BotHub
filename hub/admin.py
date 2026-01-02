from django.contrib import admin

from .models import AuditEvent, Message, Project, ProjectMembership, Tag, Task, TaskAssignment, Thread, UserProfile


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


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role", "invited_by", "created_at")
    list_filter = ("role",)
    search_fields = ("project__name", "user__username")


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
