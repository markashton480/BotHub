"""
Comprehensive model tests for hub app.
"""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from hub.models import Message, Project, ProjectMembership, Tag, Task, Thread, UserProfile
from hub.serializers import ThreadSerializer

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


class UserProfileModelTests(TestCase):
    """Tests for UserProfile model."""

    def test_create_user_profile_auto_created(self):
        """Test user profile is auto-created when user is created."""
        user = UserFactory()
        # Profile should be auto-created by signal
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsNotNone(user.profile)
        self.assertEqual(user.profile.user, user)

    def test_user_profile_str_with_display_name(self):
        """Test __str__ returns display_name when set."""
        user = UserFactory()
        user.profile.display_name = "Test Agent"
        user.profile.save()
        self.assertEqual(str(user.profile), "Test Agent")

    def test_user_profile_str_without_display_name(self):
        """Test __str__ returns username when display_name is empty."""
        user = UserFactory(username="testuser")
        user.profile.display_name = ""
        user.profile.save()
        self.assertEqual(str(user.profile), "testuser")

    def test_user_profile_kind_choices(self):
        """Test UserProfile kind choices."""
        human = UserFactory()
        human.profile.kind = UserProfile.Kind.HUMAN
        human.profile.save()

        agent = UserFactory()
        agent.profile.kind = UserProfile.Kind.AGENT
        agent.profile.save()

        self.assertEqual(human.profile.kind, "human")
        self.assertEqual(agent.profile.kind, "agent")


class ProjectModelTests(TestCase):
    """Tests for Project model."""

    def test_create_project(self):
        """Test creating a project."""
        user = UserFactory()
        project = ProjectFactory(name="Test Project", created_by=user)
        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.created_by, user)
        self.assertFalse(project.is_archived)

    def test_project_str(self):
        """Test __str__ returns project name."""
        project = ProjectFactory(name="My Project")
        self.assertEqual(str(project), "My Project")

    def test_project_ordering(self):
        """Test projects are ordered by name, then id."""
        ProjectFactory(name="Zebra")
        ProjectFactory(name="Alpha")
        ProjectFactory(name="Beta")
        projects = list(Project.objects.all())
        self.assertEqual(projects[0].name, "Alpha")
        self.assertEqual(projects[1].name, "Beta")
        self.assertEqual(projects[2].name, "Zebra")

    def test_project_archived_flag(self):
        """Test is_archived flag works."""
        project = ProjectFactory(is_archived=True)
        self.assertTrue(project.is_archived)

    def test_project_created_by_can_be_null(self):
        """Test created_by can be null (if user deleted)."""
        project = ProjectFactory(created_by=None)
        self.assertIsNone(project.created_by)


class ProjectMembershipModelTests(TestCase):
    """Tests for ProjectMembership model."""

    def test_create_membership(self):
        """Test creating a project membership."""
        user = UserFactory()
        project = ProjectFactory()
        membership = ProjectMembershipFactory(
            project=project,
            user=user,
            role=ProjectMembership.Role.ADMIN
        )
        self.assertEqual(membership.project, project)
        self.assertEqual(membership.user, user)
        self.assertEqual(membership.role, ProjectMembership.Role.ADMIN)

    def test_membership_str(self):
        """Test __str__ representation."""
        user = UserFactory(username="alice")
        project = ProjectFactory(name="Project A")
        membership = ProjectMembershipFactory(
            project=project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        expected = f"{user} -> {project} (viewer)"
        self.assertEqual(str(membership), expected)

    def test_membership_unique_constraint(self):
        """Test user cannot have duplicate membership in same project."""
        user = UserFactory()
        project = ProjectFactory()
        ProjectMembershipFactory(project=project, user=user)
        with self.assertRaises(IntegrityError):
            ProjectMembershipFactory(project=project, user=user)

    def test_membership_role_choices(self):
        """Test all membership role choices work."""
        project = ProjectFactory()
        owner = ProjectMembershipFactory(project=project, role=ProjectMembership.Role.OWNER)
        admin = ProjectMembershipFactory(project=project, role=ProjectMembership.Role.ADMIN)
        member = ProjectMembershipFactory(project=project, role=ProjectMembership.Role.MEMBER)
        viewer = ProjectMembershipFactory(project=project, role=ProjectMembership.Role.VIEWER)

        self.assertEqual(owner.role, "owner")
        self.assertEqual(admin.role, "admin")
        self.assertEqual(member.role, "member")
        self.assertEqual(viewer.role, "viewer")

    def test_membership_default_role(self):
        """Test default role is MEMBER."""
        membership = ProjectMembershipFactory()
        self.assertEqual(membership.role, ProjectMembership.Role.MEMBER)


class TagModelTests(TestCase):
    """Tests for Tag model."""

    def test_create_tag(self):
        """Test creating a tag."""
        tag = TagFactory(name="Bug Fix")
        self.assertEqual(tag.name, "Bug Fix")

    def test_tag_slug_auto_generated(self):
        """Test slug is auto-generated from name."""
        tag = Tag.objects.create(name="Feature Request")
        self.assertEqual(tag.slug, "feature-request")

    def test_tag_slug_unique(self):
        """Test tag slugs must be unique."""
        TagFactory(name="Test", slug="test")
        with self.assertRaises(IntegrityError):
            TagFactory(name="Different", slug="test")

    def test_tag_name_unique(self):
        """Test tag names must be unique."""
        TagFactory(name="Duplicate")
        with self.assertRaises(IntegrityError):
            TagFactory(name="Duplicate")

    def test_tag_str(self):
        """Test __str__ returns tag name."""
        tag = TagFactory(name="Enhancement")
        self.assertEqual(str(tag), "Enhancement")

    def test_tag_ordering(self):
        """Test tags are ordered by name."""
        TagFactory(name="Zebra")
        TagFactory(name="Alpha")
        TagFactory(name="Beta")
        tags = list(Tag.objects.all())
        self.assertEqual(tags[0].name, "Alpha")
        self.assertEqual(tags[1].name, "Beta")
        self.assertEqual(tags[2].name, "Zebra")


class TaskModelTests(TestCase):
    """Tests for Task model."""

    def test_create_task(self):
        """Test creating a task."""
        project = ProjectFactory()
        user = UserFactory()
        task = TaskFactory(
            project=project,
            title="Implement feature",
            created_by=user
        )
        self.assertEqual(task.title, "Implement feature")
        self.assertEqual(task.project, project)
        self.assertEqual(task.created_by, user)

    def test_task_str(self):
        """Test __str__ returns task title."""
        task = TaskFactory(title="Fix bug")
        self.assertEqual(str(task), "Fix bug")

    def test_task_default_status(self):
        """Test default status is BACKLOG."""
        task = TaskFactory()
        self.assertEqual(task.status, Task.Status.BACKLOG)

    def test_task_default_priority(self):
        """Test default priority is MEDIUM."""
        task = TaskFactory()
        self.assertEqual(task.priority, Task.Priority.MEDIUM)

    def test_task_parent_relationship(self):
        """Test task can have parent task in same project."""
        project = ProjectFactory()
        parent = TaskFactory(project=project, title="Parent")
        child = TaskFactory(project=project, parent=parent, title="Child")
        self.assertEqual(child.parent, parent)
        self.assertIn(child, parent.children.all())

    def test_task_parent_must_be_same_project(self):
        """Test parent task must be in same project."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        parent = TaskFactory(project=project1)
        child = TaskFactory(project=project2, parent=parent)
        with self.assertRaises(ValidationError) as cm:
            child.clean()
        self.assertIn("parent", cm.exception.message_dict)

    def test_task_cannot_be_own_parent(self):
        """Test task cannot be its own parent."""
        task = TaskFactory()
        task.parent = task
        with self.assertRaises(ValidationError) as cm:
            task.clean()
        self.assertIn("parent", cm.exception.message_dict)

    def test_task_status_choices(self):
        """Test all task status choices work."""
        backlog = TaskFactory(status=Task.Status.BACKLOG)
        todo = TaskFactory(status=Task.Status.TODO)
        in_progress = TaskFactory(status=Task.Status.IN_PROGRESS)
        blocked = TaskFactory(status=Task.Status.BLOCKED)
        done = TaskFactory(status=Task.Status.DONE)

        self.assertEqual(backlog.status, "backlog")
        self.assertEqual(todo.status, "todo")
        self.assertEqual(in_progress.status, "in_progress")
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(done.status, "done")

    def test_task_priority_choices(self):
        """Test all task priority choices work."""
        low = TaskFactory(priority=Task.Priority.LOW)
        medium = TaskFactory(priority=Task.Priority.MEDIUM)
        high = TaskFactory(priority=Task.Priority.HIGH)
        urgent = TaskFactory(priority=Task.Priority.URGENT)

        self.assertEqual(low.priority, 1)
        self.assertEqual(medium.priority, 2)
        self.assertEqual(high.priority, 3)
        self.assertEqual(urgent.priority, 4)

    def test_task_tags_many_to_many(self):
        """Test task can have multiple tags."""
        task = TaskFactory()
        tag1 = TagFactory(name="Bug")
        tag2 = TagFactory(name="Critical")
        task.tags.add(tag1, tag2)
        self.assertEqual(task.tags.count(), 2)
        self.assertIn(tag1, task.tags.all())
        self.assertIn(tag2, task.tags.all())


class ThreadModelValidationTests(TestCase):
    """Tests for Thread model validation (from original tests.py)."""

    def setUp(self):
        self.user = User.objects.create_user(username="casey", password="testpass")
        self.project = Project.objects.create(name="Project Alpha", created_by=self.user)
        self.task = Task.objects.create(project=self.project, title="Task One", created_by=self.user)

    def test_thread_requires_scope(self):
        """Test thread requires either project or task."""
        thread = Thread(title="Needs scope")
        with self.assertRaises(ValidationError):
            thread.clean()

    def test_thread_single_scope(self):
        """Test thread can only have one scope (project OR task, not both)."""
        thread = Thread(title="Too many", project=self.project, task=self.task)
        with self.assertRaises(ValidationError):
            thread.clean()


class ThreadModelTests(TestCase):
    """Additional tests for Thread model."""

    def test_create_thread_with_project(self):
        """Test creating thread attached to project."""
        project = ProjectFactory()
        thread = ThreadFactory(project=project, task=None)
        self.assertEqual(thread.project, project)
        self.assertIsNone(thread.task)

    def test_create_thread_with_task(self):
        """Test creating thread attached to task."""
        task = TaskFactory()
        thread = ThreadFactory(project=None, task=task)
        self.assertIsNone(thread.project)
        self.assertEqual(thread.task, task)

    def test_thread_str(self):
        """Test __str__ returns thread title."""
        thread = ThreadFactory(title="Discussion")
        self.assertEqual(str(thread), "Discussion")

    def test_thread_kind_choices(self):
        """Test all thread kind choices work."""
        general = ThreadFactory(kind=Thread.Kind.GENERAL)
        planning = ThreadFactory(kind=Thread.Kind.PLANNING)
        update = ThreadFactory(kind=Thread.Kind.UPDATE)

        self.assertEqual(general.kind, "general")
        self.assertEqual(planning.kind, "planning")
        self.assertEqual(update.kind, "update")

    def test_thread_default_kind(self):
        """Test default kind is GENERAL."""
        thread = ThreadFactory()
        self.assertEqual(thread.kind, Thread.Kind.GENERAL)


class ThreadSerializerValidationTests(TestCase):
    """Tests for ThreadSerializer validation (from original tests.py)."""

    def setUp(self):
        self.user = User.objects.create_user(username="jules", password="testpass")
        self.project = Project.objects.create(name="Project Beta", created_by=self.user)
        self.task = Task.objects.create(project=self.project, title="Task Two", created_by=self.user)

    def test_thread_serializer_requires_scope(self):
        """Test serializer requires either project or task."""
        serializer = ThreadSerializer(data={"title": "No scope", "kind": "general"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("project", serializer.errors)
        self.assertIn("task", serializer.errors)

    def test_thread_serializer_rejects_both_scopes(self):
        """Test serializer rejects both project and task."""
        serializer = ThreadSerializer(
            data={"title": "Both", "kind": "general", "project": self.project.id, "task": self.task.id}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("project", serializer.errors)
        self.assertIn("task", serializer.errors)


class MessageModelTests(TestCase):
    """Tests for Message model."""

    def test_create_message(self):
        """Test creating a message."""
        thread = ThreadFactory()
        user = UserFactory()
        message = MessageFactory(
            thread=thread,
            created_by=user,
            body="Test message"
        )
        self.assertEqual(message.thread, thread)
        self.assertEqual(message.created_by, user)
        self.assertEqual(message.body, "Test message")

    def test_message_str(self):
        """Test __str__ representation."""
        thread = ThreadFactory(title="Thread A")
        message = MessageFactory(thread=thread)
        # Should contain thread and date
        self.assertIn(str(thread), str(message))

    def test_message_author_role_choices(self):
        """Test all message author role choices work."""
        human = MessageFactory(author_role=Message.AuthorRole.HUMAN)
        agent = MessageFactory(author_role=Message.AuthorRole.AGENT)
        system = MessageFactory(author_role=Message.AuthorRole.SYSTEM)

        self.assertEqual(human.author_role, "human")
        self.assertEqual(agent.author_role, "agent")
        self.assertEqual(system.author_role, "system")

    def test_message_default_author_role(self):
        """Test default author role is HUMAN."""
        message = MessageFactory()
        self.assertEqual(message.author_role, Message.AuthorRole.HUMAN)

    def test_message_metadata_default(self):
        """Test metadata defaults to empty dict."""
        message = MessageFactory(metadata={})
        self.assertEqual(message.metadata, {})

    def test_message_ordering(self):
        """Test messages are ordered by created_at."""
        thread = ThreadFactory()
        msg3 = MessageFactory(thread=thread)
        msg1 = MessageFactory(thread=thread)
        msg2 = MessageFactory(thread=thread)
        messages = list(Message.objects.filter(thread=thread))
        # Should be ordered by creation time
        self.assertEqual(messages[0], msg3)
        self.assertEqual(messages[1], msg1)
        self.assertEqual(messages[2], msg2)
