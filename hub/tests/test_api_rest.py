"""
Comprehensive REST API tests using Django REST Framework.
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from hub.models import Message, Project, ProjectMembership, Tag, Task, Thread

from .factories import (
    MessageFactory,
    ProjectFactory,
    ProjectMembershipFactory,
    TagFactory,
    TaskFactory,
    ThreadFactory,
    UserFactory,
    UserProfileFactory,
)

User = get_user_model()


class ProjectAPITests(APITestCase):
    """Tests for Project API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_projects_authenticated(self):
        """Test listing projects returns only user's projects."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        project3 = ProjectFactory()

        # User has access to project1 and project2
        ProjectMembershipFactory(project=project1, user=self.user)
        ProjectMembershipFactory(project=project2, user=self.user)

        url = reverse("project-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        project_ids = [p["id"] for p in response.data]
        self.assertIn(project1.id, project_ids)
        self.assertIn(project2.id, project_ids)
        self.assertNotIn(project3.id, project_ids)

    def test_list_projects_unauthenticated(self):
        """Test unauthenticated users cannot list projects."""
        self.client.force_authenticate(user=None)
        url = reverse("project-list")
        response = self.client.get(url)
        # DRF returns 403 for session auth without credentials
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_create_project(self):
        """Test creating a new project."""
        url = reverse("project-list")
        data = {"name": "New Project", "description": "Test description"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Project")
        self.assertEqual(response.data["created_by"], self.user.id)

        # Verify project created
        project = Project.objects.get(id=response.data["id"])
        self.assertEqual(project.name, "New Project")

    def test_create_project_auto_owner_membership(self):
        """Test project creator automatically becomes OWNER."""
        url = reverse("project-list")
        data = {"name": "Auto Owner Test"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        project_id = response.data["id"]

        # Check OWNER membership was created
        membership = ProjectMembership.objects.get(
            project_id=project_id,
            user=self.user
        )
        self.assertEqual(membership.role, ProjectMembership.Role.OWNER)

    def test_retrieve_project(self):
        """Test retrieving a specific project."""
        project = ProjectFactory()
        ProjectMembershipFactory(project=project, user=self.user)

        url = reverse("project-detail", args=[project.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], project.id)
        self.assertEqual(response.data["name"], project.name)

    def test_retrieve_project_permission_denied(self):
        """Test non-member cannot retrieve project."""
        project = ProjectFactory()

        url = reverse("project-detail", args=[project.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_project_requires_member_role(self):
        """Test VIEWER cannot update project."""
        project = ProjectFactory()
        ProjectMembershipFactory(
            project=project,
            user=self.user,
            role=ProjectMembership.Role.VIEWER
        )

        url = reverse("project-detail", args=[project.id])
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_project_member_can_edit(self):
        """Test MEMBER can update project."""
        project = ProjectFactory()
        ProjectMembershipFactory(
            project=project,
            user=self.user,
            role=ProjectMembership.Role.MEMBER
        )

        url = reverse("project-detail", args=[project.id])
        data = {"name": "Updated Name"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Updated Name")

    def test_delete_project_requires_owner(self):
        """Test only OWNER can delete project."""
        project = ProjectFactory()
        ProjectMembershipFactory(
            project=project,
            user=self.user,
            role=ProjectMembership.Role.ADMIN
        )

        url = reverse("project-detail", args=[project.id])
        response = self.client.delete(url)

        # ADMIN cannot delete, only OWNER can
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_project_owner_can_delete(self):
        """Test OWNER can delete project."""
        project = ProjectFactory()
        ProjectMembershipFactory(
            project=project,
            user=self.user,
            role=ProjectMembership.Role.OWNER
        )

        url = reverse("project-detail", args=[project.id])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Project.objects.filter(id=project.id).exists())


class TaskAPITests(APITestCase):
    """Tests for Task API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_list_tasks_filtered_by_membership(self):
        """Test tasks are filtered by project membership."""
        task1 = TaskFactory(project=self.project)
        task2 = TaskFactory(project=self.project)
        # Task from inaccessible project
        other_task = TaskFactory()

        url = reverse("task-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        task_ids = [t["id"] for t in response.data]
        self.assertIn(task1.id, task_ids)
        self.assertIn(task2.id, task_ids)
        self.assertNotIn(other_task.id, task_ids)

    def test_list_tasks_filtered_by_project(self):
        """Test ?project=X filter works."""
        project2 = ProjectFactory()
        ProjectMembershipFactory(project=project2, user=self.user)

        task1 = TaskFactory(project=self.project)
        TaskFactory(project=project2)

        url = reverse("task-list")
        response = self.client.get(url, {"project": self.project.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], task1.id)

    def test_list_tasks_filtered_by_parent(self):
        """Test ?parent=X filter works."""
        parent = TaskFactory(project=self.project)
        child1 = TaskFactory(project=self.project, parent=parent)
        child2 = TaskFactory(project=self.project, parent=parent)
        standalone = TaskFactory(project=self.project)

        url = reverse("task-list")
        response = self.client.get(url, {"parent": parent.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        task_ids = [t["id"] for t in response.data]
        self.assertIn(child1.id, task_ids)
        self.assertIn(child2.id, task_ids)
        self.assertNotIn(standalone.id, task_ids)

    def test_create_task(self):
        """Test creating a task."""
        url = reverse("task-list")
        data = {
            "project": self.project.id,
            "title": "New Task",
            "description": "Test description",
            "status": "todo",
            "priority": 2
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Task")
        self.assertEqual(response.data["created_by"], self.user.id)

    def test_create_task_with_tags(self):
        """Test creating task with tags."""
        tag1 = TagFactory()
        tag2 = TagFactory()

        url = reverse("task-list")
        data = {
            "project": self.project.id,
            "title": "Tagged Task",
            "tags": [tag1.id, tag2.id]
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["tags"]), 2)

    def test_update_task_requires_member_role(self):
        """Test VIEWER cannot update task."""
        task = TaskFactory(project=self.project)

        # Change user to VIEWER
        membership = ProjectMembership.objects.get(project=self.project, user=self.user)
        membership.role = ProjectMembership.Role.VIEWER
        membership.save()

        url = reverse("task-detail", args=[task.id])
        data = {"title": "Updated Title"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_task_member_can_edit(self):
        """Test MEMBER can update task."""
        task = TaskFactory(project=self.project)

        url = reverse("task-detail", args=[task.id])
        data = {"status": "done"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "done")

    def test_create_task_invalid_parent_project(self):
        """Test parent task must be in same project."""
        other_project = ProjectFactory()
        parent = TaskFactory(project=other_project)

        url = reverse("task-list")
        data = {
            "project": self.project.id,
            "title": "Invalid Parent Task",
            "parent": parent.id
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("parent", response.data)


class ThreadAPITests(APITestCase):
    """Tests for Thread API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_list_threads_filtered_by_membership(self):
        """Test threads are filtered by project membership."""
        thread1 = ThreadFactory(project=self.project, task=None)
        thread2 = ThreadFactory(project=self.project, task=None)
        # Thread from inaccessible project
        other_thread = ThreadFactory()

        url = reverse("thread-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        thread_ids = [t["id"] for t in response.data]
        self.assertIn(thread1.id, thread_ids)
        self.assertIn(thread2.id, thread_ids)
        self.assertNotIn(other_thread.id, thread_ids)

    def test_create_thread_with_project(self):
        """Test creating thread attached to project."""
        url = reverse("thread-list")
        data = {
            "title": "New Thread",
            "kind": "planning",
            "project": self.project.id
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Thread")
        self.assertEqual(response.data["project"], self.project.id)
        self.assertIsNone(response.data["task"])

    def test_create_thread_with_task(self):
        """Test creating thread attached to task."""
        task = TaskFactory(project=self.project)

        url = reverse("thread-list")
        data = {
            "title": "Task Thread",
            "kind": "update",
            "task": task.id
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["task"], task.id)
        self.assertIsNone(response.data["project"])

    def test_create_thread_requires_scope(self):
        """Test thread creation requires project or task."""
        url = reverse("thread-list")
        data = {"title": "No Scope Thread", "kind": "general"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project", response.data)
        self.assertIn("task", response.data)

    def test_create_thread_rejects_both_scopes(self):
        """Test thread cannot have both project and task."""
        task = TaskFactory(project=self.project)

        url = reverse("thread-list")
        data = {
            "title": "Both Scopes",
            "kind": "general",
            "project": self.project.id,
            "task": task.id
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MessageAPITests(APITestCase):
    """Tests for Message API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.thread = ThreadFactory(project=self.project, task=None)
        self.client.force_authenticate(user=self.user)

    def test_list_messages_filtered_by_membership(self):
        """Test messages are filtered by project membership."""
        msg1 = MessageFactory(thread=self.thread)
        msg2 = MessageFactory(thread=self.thread)
        # Message from inaccessible thread
        other_msg = MessageFactory()

        url = reverse("message-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        msg_ids = [m["id"] for m in response.data]
        self.assertIn(msg1.id, msg_ids)
        self.assertIn(msg2.id, msg_ids)
        self.assertNotIn(other_msg.id, msg_ids)

    def test_list_messages_filtered_by_thread(self):
        """Test ?thread=X filter works."""
        thread2 = ThreadFactory(project=self.project, task=None)

        msg1 = MessageFactory(thread=self.thread)
        MessageFactory(thread=thread2)

        url = reverse("message-list")
        response = self.client.get(url, {"thread": self.thread.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], msg1.id)

    def test_create_message(self):
        """Test creating a message."""
        url = reverse("message-list")
        data = {
            "thread": self.thread.id,
            "body": "Test message content"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["body"], "Test message content")
        self.assertEqual(response.data["created_by"], self.user.id)

    def test_create_message_auto_fills_author_label(self):
        """Test author_label auto-filled from username."""
        url = reverse("message-list")
        data = {
            "thread": self.thread.id,
            "body": "Auto author test"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author_label"], self.user.username)

    def test_create_message_auto_detects_agent_role(self):
        """Test author_role auto-set to 'agent' for agent users."""
        agent_user = UserFactory()
        # Update the auto-created profile to be an agent
        agent_user.profile.kind = "agent"
        agent_user.profile.save()
        ProjectMembershipFactory(project=self.project, user=agent_user)

        self.client.force_authenticate(user=agent_user)

        url = reverse("message-list")
        data = {
            "thread": self.thread.id,
            "body": "Agent message"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author_role"], "agent")


class TagAPITests(APITestCase):
    """Tests for Tag API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_tags(self):
        """Test listing all tags."""
        TagFactory()
        TagFactory()

        url = reverse("tag-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_create_tag(self):
        """Test creating a tag."""
        url = reverse("tag-list")
        data = {"name": "New Tag", "color": "#FF5733"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Tag")
        # Slug should be auto-generated
        self.assertEqual(response.data["slug"], "new-tag")

    def test_create_tag_duplicate_name(self):
        """Test creating tag with duplicate name fails."""
        TagFactory(name="Duplicate")

        url = reverse("tag-list")
        data = {"name": "Duplicate"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProjectMembershipAPITests(APITestCase):
    """Tests for ProjectMembership API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.ADMIN
        )
        self.client.force_authenticate(user=self.user)

    def test_list_memberships_filtered_by_project_access(self):
        """Test memberships are filtered by project access."""
        # User can see this project's memberships
        member1 = ProjectMembershipFactory(project=self.project)

        # User cannot see this project's memberships
        other_project = ProjectFactory()
        member2 = ProjectMembershipFactory(project=other_project)

        url = reverse("membership-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership_ids = [m["id"] for m in response.data]
        self.assertIn(member1.id, membership_ids)
        self.assertNotIn(member2.id, membership_ids)

    def test_create_membership_requires_edit_permission(self):
        """Test VIEWER cannot create memberships."""
        # Change user to VIEWER
        membership = ProjectMembership.objects.get(project=self.project, user=self.user)
        membership.role = ProjectMembership.Role.VIEWER
        membership.save()

        new_user = UserFactory()
        url = reverse("membership-list")
        data = {
            "project": self.project.id,
            "user": new_user.id,
            "role": "member"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_membership_admin_can_add(self):
        """Test ADMIN can add members."""
        new_user = UserFactory()
        url = reverse("membership-list")
        data = {
            "project": self.project.id,
            "user": new_user.id,
            "role": "member"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["role"], "member")
        self.assertEqual(response.data["invited_by"], self.user.id)


class AuditEventAPITests(APITestCase):
    """Tests for AuditEvent API endpoints."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_audit_events_read_only(self):
        """Test audit events are read-only."""
        url = reverse("audit-event-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Try to create - should not be allowed
        data = {"verb": "test.action"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_audit_events_filtered_by_project_access(self):
        """Test audit events are filtered to accessible projects."""
        from hub.audit import log_event

        accessible_project = ProjectFactory()
        ProjectMembershipFactory(project=accessible_project, user=self.user)

        inaccessible_project = ProjectFactory()

        # Create events
        event1 = log_event(self.user, "project.created", accessible_project)
        event2 = log_event(self.user, "project.created", inaccessible_project)

        url = reverse("audit-event-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event_ids = [e["id"] for e in response.data]
        self.assertIn(event1.id, event_ids)
        self.assertNotIn(event2.id, event_ids)


class ValidationTests(APITestCase):
    """Tests for API validation."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_create_task_missing_required_field(self):
        """Test creating task without required field fails."""
        url = reverse("task-list")
        data = {"project": self.project.id}  # Missing title
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_create_task_invalid_status(self):
        """Test creating task with invalid status fails."""
        url = reverse("task-list")
        data = {
            "project": self.project.id,
            "title": "Test Task",
            "status": "invalid_status"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_membership_invalid_role(self):
        """Test creating membership with invalid role fails."""
        new_user = UserFactory()

        # Make user ADMIN first
        membership = ProjectMembership.objects.get(project=self.project, user=self.user)
        membership.role = ProjectMembership.Role.ADMIN
        membership.save()

        url = reverse("membership-list")
        data = {
            "project": self.project.id,
            "user": new_user.id,
            "role": "invalid_role"
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EdgeCaseTests(APITestCase):
    """Tests for edge cases."""

    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_nonexistent_project(self):
        """Test retrieving nonexistent project returns 404."""
        url = reverse("project-detail", args=[99999])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_nonexistent_task(self):
        """Test updating nonexistent task returns 404."""
        url = reverse("task-detail", args=[99999])
        data = {"title": "Updated"}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_thread(self):
        """Test deleting nonexistent thread returns 404."""
        url = reverse("thread-detail", args=[99999])
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
