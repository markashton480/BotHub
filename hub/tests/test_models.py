"""Model tests."""
from django.test import TestCase
from .factories import (
    UserFactory, ProjectFactory, ProjectMembershipFactory,
    TaskFactory, ThreadFactory, MessageFactory, TagFactory
)


class ProjectModelTests(TestCase):
    def test_project_str(self):
        project = ProjectFactory(name="Test Project")
        self.assertEqual(str(project), "Test Project")

    def test_project_membership_created(self):
        project = ProjectFactory()
        membership = ProjectMembershipFactory(project=project)
        self.assertEqual(membership.project, project)


class TaskModelTests(TestCase):
    def test_task_str(self):
        task = TaskFactory(title="Test Task")
        self.assertEqual(str(task), "Test Task")

    def test_task_belongs_to_project(self):
        project = ProjectFactory()
        task = TaskFactory(project=project)
        self.assertEqual(task.project, project)


class ThreadModelTests(TestCase):
    def test_thread_str(self):
        thread = ThreadFactory(title="Test Thread")
        self.assertEqual(str(thread), "Test Thread")


class MessageModelTests(TestCase):
    def test_message_belongs_to_thread(self):
        thread = ThreadFactory()
        message = MessageFactory(thread=thread)
        self.assertEqual(message.thread, thread)


class TagModelTests(TestCase):
    def test_tag_str(self):
        tag = TagFactory(name="urgent")
        self.assertEqual(str(tag), "urgent")
