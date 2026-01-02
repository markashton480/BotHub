import time

from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.template.response import TemplateResponse
from django.urls import path, reverse

from hub.models import AuditEvent, Message, Project, Tag, Task, Thread, Webhook

User = get_user_model()


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
        started = time.monotonic()
        query = (request.GET.get("s") or "").strip()
        results = []

        def add_results(queryset, title_attr, description, icon):
            for obj in queryset:
                results.append(
                    {
                        "title": getattr(obj, title_attr),
                        "description": description,
                        "icon": icon,
                        "link": reverse(
                            f"{self.name}:{obj._meta.app_label}_{obj._meta.model_name}_change",
                            args=[obj.pk],
                        ),
                    }
                )

        if query:
            add_results(
                Project.objects.filter(name__icontains=query)[:20],
                "name",
                "Project",
                "folder",
            )
            add_results(
                Task.objects.filter(title__icontains=query)[:20],
                "title",
                "Task",
                "check-circle",
            )
            add_results(
                Thread.objects.filter(title__icontains=query)[:20],
                "title",
                "Thread",
                "chat-bubble-left-right",
            )
            add_results(
                Message.objects.filter(body__icontains=query)[:20],
                "body",
                "Message",
                "chat-bubble-left",
            )
            add_results(
                Tag.objects.filter(name__icontains=query)[:20],
                "name",
                "Tag",
                "tag",
            )
            add_results(
                Webhook.objects.filter(name__icontains=query)[:20],
                "name",
                "Webhook",
                "bolt",
            )
            add_results(
                User.objects.filter(username__icontains=query)[:20],
                "username",
                "User",
                "user",
            )
            add_results(
                AuditEvent.objects.filter(verb__icontains=query)[:20],
                "verb",
                "Audit",
                "clock",
            )

        paginator = Paginator(results, 10)
        page = paginator.get_page(request.GET.get("page", 1))
        page_counter = (page.number - 1) * paginator.per_page
        context = {
            "results": page,
            "page_obj": page,
            "page_counter": page_counter,
            "execution_time": time.monotonic() - started,
            "command_show_history": False,
        }
        return TemplateResponse(
            request, "unfold/helpers/command_results.html", context
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


bot_admin_site = BotHubAdminSite(name="admin")
