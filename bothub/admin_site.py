from django.contrib.admin import AdminSite
from django.http import HttpResponse
from django.urls import path

from hub.models import AuditEvent, Message, Project, Tag, Task, Thread, Webhook


class BotHubAdminSite(AdminSite):
    site_header = "BotHub Admin"
    site_title = "BotHub Admin"
    index_title = "Dashboard"
    index_template = "admin/index.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("search/", self.admin_view(self.command_search), name="search"),
        ]
        return custom_urls + urls

    def command_search(self, request):
        # Unfold command palette expects these IDs in the response.
        return HttpResponse(
            '<div id="command-results-list"></div><div id="command-results-note"></div>'
        )

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["stats"] = {
            "projects": Project.objects.count(),
            "tasks": Task.objects.count(),
            "threads": Thread.objects.count(),
            "messages": Message.objects.count(),
            "tags": Tag.objects.count(),
            "webhooks": Webhook.objects.count(),
            "audit_events": AuditEvent.objects.count(),
        }
        return super().index(request, extra_context=extra_context)


bot_admin_site = BotHubAdminSite(name="bothub_admin")
