from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.db import connection
from django.template.response import TemplateResponse
from django.urls import path
from unfold.sites import UnfoldAdminSite

from hub.models import AuditEvent

User = get_user_model()


class BotHubAdminSite(UnfoldAdminSite):
    site_header = "BotHub Admin"
    site_title = "BotHub Admin"
    index_title = "Dashboard"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("", self.admin_view(self.dashboard_view), name="index"),
            path("dashboard/", self.admin_view(self.dashboard_view), name="dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        # Optimize stats collection with a single database query
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM hub_project) as projects,
                    (SELECT COUNT(*) FROM hub_task) as tasks,
                    (SELECT COUNT(*) FROM hub_thread) as threads,
                    (SELECT COUNT(*) FROM hub_message) as messages,
                    (SELECT COUNT(*) FROM auth_user) as users
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
            AuditEvent.objects.select_related("actor").order_by("-created_at")[:10]
        )
        recent_log_entries = (
            LogEntry.objects.select_related("user", "content_type")
            .order_by("-action_time")[:10]
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
