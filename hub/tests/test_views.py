"""
Comprehensive tests for HTML views.
"""
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse

from hub.models import Message, Project, ProjectMembership, Task, Thread

from .factories import (
    MessageFactory,
    ProjectFactory,
    ProjectMembershipFactory,
    TaskFactory,
    ThreadFactory,
    UserFactory,
)


class HomeViewTests(TestCase):
    """Tests for home view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("hub:home")

    def test_home_requires_login(self):
        """Test home view requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_home_shows_user_projects(self):
        """Test home view shows only user's accessible projects."""
        self.client.force_login(self.user)

        # Create projects with memberships
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        project3 = ProjectFactory()  # User not a member

        ProjectMembershipFactory(project=project1, user=self.user)
        ProjectMembershipFactory(project=project2, user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, project1.name)
        self.assertContains(response, project2.name)
        self.assertNotContains(response, project3.name)

    def test_home_context_includes_project_form(self):
        """Test home view context includes project form."""
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("project_form", response.context)
        self.assertIn("projects", response.context)


class ProjectCreateViewTests(TestCase):
    """Tests for project_create view."""

    def setUp(self):
        self.user = UserFactory()
        self.url = reverse("hub:project-create")

    def test_project_create_requires_login(self):
        """Test project create requires authentication."""
        response = self.client.post(self.url, {"name": "New Project"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_project_create_get_redirects(self):
        """Test GET request redirects to home."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_project_create_via_form(self):
        """Test creating project via POST."""
        self.client.force_login(self.user)

        data = {
            "name": "Test Project",
            "description": "Test description"
        }
        response = self.client.post(self.url, data)

        # Check project created
        project = Project.objects.get(name="Test Project")
        self.assertEqual(project.description, "Test description")
        self.assertEqual(project.created_by, self.user)

        # Check OWNER membership auto-created
        membership = ProjectMembership.objects.get(project=project, user=self.user)
        self.assertEqual(membership.role, ProjectMembership.Role.OWNER)

    def test_project_create_invalid_form(self):
        """Test creating project with invalid data."""
        self.client.force_login(self.user)

        # Empty name should fail
        response = self.client.post(self.url, {"name": ""})
        self.assertEqual(response.status_code, 400)

    def test_project_create_htmx_response(self):
        """Test HTMX request returns partial HTML."""
        self.client.force_login(self.user)

        data = {"name": "HTMX Project"}
        response = self.client.post(
            self.url,
            data,
            HTTP_HX_REQUEST="true"
        )

        self.assertEqual(response.status_code, 200)
        # Should contain partial template content
        self.assertContains(response, "HTMX Project")


class ProjectDetailViewTests(TestCase):
    """Tests for project_detail view."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.url = reverse("hub:project-detail", args=[self.project.id])

    def test_project_detail_requires_login(self):
        """Test project detail requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_project_detail_permission_denied(self):
        """Test non-member gets 403."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_project_detail_shows_for_member(self):
        """Test project detail shows for project member."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project.name)

    def test_project_detail_context_includes_tasks(self):
        """Test context includes tasks."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        task1 = TaskFactory(project=self.project)
        task2 = TaskFactory(project=self.project)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("task_tree", response.context)
        self.assertIn("threads", response.context)

    def test_project_detail_context_includes_threads(self):
        """Test context includes threads."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        thread1 = ThreadFactory(project=self.project, task=None)
        thread2 = ThreadFactory(project=self.project, task=None)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        threads = response.context["threads"]
        self.assertEqual(threads.count(), 2)


class TaskCreateViewTests(TestCase):
    """Tests for task_create view."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.url = reverse("hub:task-create", args=[self.project.id])

    def test_task_create_requires_login(self):
        """Test task create requires authentication."""
        response = self.client.post(self.url, {"title": "New Task"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_task_create_requires_member_permission(self):
        """Test VIEWER cannot create tasks."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.VIEWER
        )

        response = self.client.post(self.url, {"title": "New Task"})
        self.assertEqual(response.status_code, 403)

    def test_task_create_via_form(self):
        """Test creating task via POST."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.MEMBER
        )

        data = {
            "title": "Test Task",
            "description": "Test description",
            "status": "todo",
            "priority": 2
        }
        response = self.client.post(self.url, data)

        # Check task created
        task = Task.objects.get(title="Test Task")
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.created_by, self.user)
        self.assertEqual(task.status, "todo")

    def test_task_create_htmx_returns_task_tree(self):
        """Test HTMX request returns updated task tree."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        data = {"title": "HTMX Task"}
        response = self.client.post(
            self.url,
            data,
            HTTP_HX_REQUEST="true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HTMX Task")


class ThreadCreateViewTests(TestCase):
    """Tests for thread_create view."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.url = reverse("hub:thread-create", args=[self.project.id])

    def test_thread_create_requires_login(self):
        """Test thread create requires authentication."""
        response = self.client.post(self.url, {"title": "New Thread"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_thread_create_requires_member_permission(self):
        """Test VIEWER cannot create threads."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.VIEWER
        )

        response = self.client.post(self.url, {"title": "New Thread", "kind": "general"})
        self.assertEqual(response.status_code, 403)

    def test_thread_create_via_form(self):
        """Test creating thread via POST."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        data = {
            "title": "Test Thread",
            "kind": "planning"
        }
        response = self.client.post(self.url, data)

        # Check thread created
        thread = Thread.objects.get(title="Test Thread")
        self.assertEqual(thread.project, self.project)
        self.assertEqual(thread.created_by, self.user)
        self.assertEqual(thread.kind, "planning")

    def test_thread_create_htmx_returns_thread_row(self):
        """Test HTMX request returns thread row partial."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        data = {"title": "HTMX Thread", "kind": "general"}
        response = self.client.post(
            self.url,
            data,
            HTTP_HX_REQUEST="true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HTMX Thread")


class ThreadDetailViewTests(TestCase):
    """Tests for thread_detail view."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.thread = ThreadFactory(project=self.project, task=None)
        self.url = reverse("hub:thread-detail", args=[self.thread.id])

    def test_thread_detail_requires_login(self):
        """Test thread detail requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_thread_detail_permission_denied(self):
        """Test non-member gets 403."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_thread_detail_shows_for_member(self):
        """Test thread detail shows for project member."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.thread.title)

    def test_thread_detail_context_includes_messages(self):
        """Test context includes messages."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        msg1 = MessageFactory(thread=self.thread)
        msg2 = MessageFactory(thread=self.thread)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        messages = response.context["messages"]
        self.assertEqual(messages.count(), 2)


class MessageCreateViewTests(TestCase):
    """Tests for message_create view."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        self.thread = ThreadFactory(project=self.project, task=None)
        self.url = reverse("hub:message-create", args=[self.thread.id])

    def test_message_create_requires_login(self):
        """Test message create requires authentication."""
        response = self.client.post(self.url, {"body": "New message"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_message_create_requires_member_permission(self):
        """Test VIEWER cannot create messages."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.VIEWER
        )

        response = self.client.post(self.url, {"body": "New message"})
        self.assertEqual(response.status_code, 403)

    def test_message_create_via_form(self):
        """Test creating message via POST."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        data = {"body": "Test message content"}
        response = self.client.post(self.url, data)

        # Check message created
        message = Message.objects.get(body="Test message content")
        self.assertEqual(message.thread, self.thread)
        self.assertEqual(message.created_by, self.user)

    def test_message_create_sets_author_label(self):
        """Test author_label is auto-set to username if empty."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        data = {"body": "Test message"}
        response = self.client.post(self.url, data)

        message = Message.objects.get(body="Test message")
        self.assertEqual(message.author_label, self.user.username)

    def test_message_create_htmx_returns_message_row(self):
        """Test HTMX request returns message row partial."""
        self.client.force_login(self.user)
        ProjectMembershipFactory(project=self.project, user=self.user)

        data = {"body": "HTMX message"}
        response = self.client.post(
            self.url,
            data,
            HTTP_HX_REQUEST="true"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "HTMX message")


class ViewHelperFunctionTests(TestCase):
    """Tests for view helper functions."""

    def test_build_task_tree(self):
        """Test build_task_tree creates correct hierarchical structure."""
        from hub.views import build_task_tree

        project = ProjectFactory()
        parent = TaskFactory(project=project, parent=None)
        child1 = TaskFactory(project=project, parent=parent)
        child2 = TaskFactory(project=project, parent=parent)
        standalone = TaskFactory(project=project, parent=None)

        tasks = [parent, child1, child2, standalone]
        tree = build_task_tree(tasks)

        # Should have 2 root nodes (parent and standalone)
        self.assertEqual(len(tree), 2)

        # Find parent node
        parent_node = next(n for n in tree if n["task"] == parent)
        self.assertEqual(len(parent_node["children"]), 2)

        # Standalone should have no children
        standalone_node = next(n for n in tree if n["task"] == standalone)
        self.assertEqual(len(standalone_node["children"]), 0)
