from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
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
        stats = {
            "projects": Project.objects.count(),
            "tasks": Task.objects.count(),
            "threads": Thread.objects.count(),
            "messages": Message.objects.count(),
            "users": User.objects.count(),
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
