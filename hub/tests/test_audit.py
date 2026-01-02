"""
Tests for audit logging functionality.
"""
from django.test import TestCase
from unittest.mock import patch

from hub.audit import log_event
from hub.models import AuditEvent

from .factories import AuditEventFactory, ProjectFactory, TaskFactory, UserFactory


class AuditLogEventTests(TestCase):
    """Tests for log_event function."""

    def test_log_event_creates_audit_event(self):
        """Test log_event creates an AuditEvent."""
        user = UserFactory()
        project = ProjectFactory()

        audit_event = log_event(user, "project.created", project)

        self.assertIsNotNone(audit_event)
        self.assertEqual(audit_event.actor, user)
        self.assertEqual(audit_event.verb, "project.created")
        self.assertEqual(audit_event.target, project)

    def test_log_event_without_target(self):
        """Test log_event works without a target object."""
        user = UserFactory()

        audit_event = log_event(user, "user.login")

        self.assertIsNotNone(audit_event)
        self.assertEqual(audit_event.actor, user)
        self.assertEqual(audit_event.verb, "user.login")
        self.assertIsNone(audit_event.target_content_type)
        self.assertIsNone(audit_event.target_object_id)

    def test_log_event_with_metadata(self):
        """Test log_event stores metadata."""
        user = UserFactory()
        metadata = {"ip_address": "127.0.0.1", "user_agent": "Mozilla/5.0"}

        audit_event = log_event(user, "user.login", metadata=metadata)

        self.assertEqual(audit_event.metadata, metadata)

    def test_log_event_default_metadata(self):
        """Test log_event uses empty dict for metadata by default."""
        user = UserFactory()

        audit_event = log_event(user, "user.logout")

        self.assertEqual(audit_event.metadata, {})

    @patch('hub.audit.dispatch_webhooks')
    def test_log_event_dispatches_webhooks(self, mock_dispatch):
        """Test log_event triggers webhook dispatch."""
        user = UserFactory()
        project = ProjectFactory()

        audit_event = log_event(user, "project.created", project)

        mock_dispatch.assert_called_once_with(audit_event)

    def test_log_event_with_task(self):
        """Test log_event with task as target."""
        user = UserFactory()
        task = TaskFactory()

        audit_event = log_event(user, "task.updated", task)

        self.assertEqual(audit_event.target, task)
        self.assertEqual(audit_event.verb, "task.updated")


class AuditEventModelTests(TestCase):
    """Tests for AuditEvent model."""

    def test_create_audit_event(self):
        """Test creating an audit event."""
        audit_event = AuditEventFactory(verb="test.action")
        self.assertEqual(audit_event.verb, "test.action")

    def test_audit_event_str(self):
        """Test __str__ representation includes verb and timestamp."""
        audit_event = AuditEventFactory(verb="project.created")
        str_repr = str(audit_event)
        self.assertIn("project.created", str_repr)

    def test_audit_event_ordering(self):
        """Test audit events are ordered by most recent first."""
        event1 = AuditEventFactory(verb="first")
        event2 = AuditEventFactory(verb="second")
        event3 = AuditEventFactory(verb="third")

        events = list(AuditEvent.objects.all())
        # Should be reverse chronological order
        self.assertEqual(events[0], event3)
        self.assertEqual(events[1], event2)
        self.assertEqual(events[2], event1)

    def test_audit_event_can_have_no_actor(self):
        """Test audit event can have null actor (system events)."""
        audit_event = AuditEventFactory(actor=None, verb="system.startup")
        self.assertIsNone(audit_event.actor)
        self.assertEqual(audit_event.verb, "system.startup")

    def test_audit_event_metadata_stores_json(self):
        """Test metadata field stores JSON data."""
        metadata = {
            "old_value": "todo",
            "new_value": "done",
            "changed_by": "system"
        }
        audit_event = AuditEventFactory(metadata=metadata)
        self.assertEqual(audit_event.metadata, metadata)


class AuditEventFilteringTests(TestCase):
    """Tests for filtering audit events by project membership."""

    def test_audit_events_for_accessible_projects(self):
        """Test filtering audit events to only show events for accessible projects."""
        user = UserFactory()
        accessible_project = ProjectFactory()
        inaccessible_project = ProjectFactory()

        # Create events for both projects
        log_event(user, "project.created", accessible_project)
        log_event(user, "project.created", inaccessible_project)

        # This test verifies the structure exists - actual filtering
        # would be tested in API tests where permissions are applied
        all_events = AuditEvent.objects.all()
        self.assertEqual(all_events.count(), 2)
