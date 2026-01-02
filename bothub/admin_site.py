from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.db import connection
from django.template.response import TemplateResponse
from django.urls import path
from unfold.sites import UnfoldAdminSite

from hub.models import AuditEvent, Message, Project, Task, Thread

User = get_user_model()


class BotHubAdminSite(UnfoldAdminSite):
    site_header = "BotHub Admin"
    site_title = "BotHub Admin"
    index_title = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("", self.admin_view(self.dashboard_view), name="index"),
            path("dashboard/", self.admin_view(self.dashboard_view), name="dashboard"),
        ]
        return custom + urls

    def dashboard_view(self, request):
        # Single round-trip to collect counts
        with connection.cursor() as cursor:
            project_table = connection.ops.quote_name(Project._meta.db_table)
            task_table = connection.ops.quote_name(Task._meta.db_table)
            thread_table = connection.ops.quote_name(Thread._meta.db_table)
            message_table = connection.ops.quote_name(Message._meta.db_table)
            user_table = connection.ops.quote_name(User._meta.db_table)
            cursor.execute(
                f"""
                SELECT
                    (SELECT COUNT(*) FROM {project_table}) AS projects,
                    (SELECT COUNT(*) FROM {task_table}) AS tasks,
                    (SELECT COUNT(*) FROM {thread_table}) AS threads,
                    (SELECT COUNT(*) FROM {message_table}) AS messages,
                    (SELECT COUNT(*) FROM {user_table}) AS users
                """
            )
            row = cursor.fetchone()
        stats = {
            "projects": row[0],
            "tasks": row[1],
            "threads": row[2],
            "messages": row[3],
            "users": row[4],
        }
        recent_audit_events = (
            AuditEvent.objects.select_related("actor").order_by("-created_at")[:8]
        )
        recent_log_entries = (
            LogEntry.objects.select_related("user", "content_type")
            .order_by("-action_time")[:8]
        )
        context = {
            **self.each_context(request),
            "title": "Dashboard",
            "stats": stats,
            "recent_audit_events": recent_audit_events,
            "recent_log_entries": recent_log_entries,
        }
        return TemplateResponse(request, "admin/dashboard.html", context)


bot_admin_site = BotHubAdminSite(name="admin")
