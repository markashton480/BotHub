from django.contrib.admin.models import LogEntry, ADDITION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from hub.models import AuditEvent, Message, Project, Task, Thread


class AdminDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pass"
        )
        self.client.login(username="admin", password="pass")

    def _build_data(self):
        project = Project.objects.create(name="Project One", created_by=self.admin_user)
        Task.objects.create(project=project, title="Task One", created_by=self.admin_user)
        thread = Thread.objects.create(title="Thread One", project=project, created_by=self.admin_user)
        Message.objects.create(thread=thread, body="Hi", created_by=self.admin_user)

    def test_dashboard_renders_with_stats(self):
        self._build_data()

        url = reverse("admin:index")
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("stats", resp.context)
        stats = resp.context["stats"]
        self.assertEqual(stats["projects"], 1)
        self.assertEqual(stats["tasks"], 1)
        self.assertEqual(stats["threads"], 1)
        self.assertEqual(stats["messages"], 1)
        self.assertGreaterEqual(stats["users"], 1)

    def test_recent_lists_are_limited_to_eight(self):
        self._build_data()

        for i in range(10):
            AuditEvent.objects.create(actor=self.admin_user, verb=f"event-{i}")

        ct = ContentType.objects.get_for_model(Project)
        for i in range(10):
            LogEntry.objects.log_action(
                user_id=self.admin_user.pk,
                content_type_id=ct.pk,
                object_id="1",
                object_repr=f"Project {i}",
                action_flag=ADDITION,
                change_message="created",
            )

        resp = self.client.get(reverse("admin:index"))
        self.assertEqual(resp.status_code, 200)

        audit_events = list(resp.context["recent_audit_events"])
        admin_logs = list(resp.context["recent_log_entries"])
        self.assertLessEqual(len(audit_events), 8)
        self.assertLessEqual(len(admin_logs), 8)
        self.assertGreaterEqual(len(audit_events), 1)
        self.assertGreaterEqual(len(admin_logs), 1)
        # Verify ordering is newest-first
        self.assertGreaterEqual(audit_events[0].created_at, audit_events[-1].created_at)
        self.assertGreaterEqual(admin_logs[0].action_time, admin_logs[-1].action_time)
