from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Project, Task, Thread
from .serializers import ThreadSerializer

User = get_user_model()


class ThreadModelValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="casey", password="testpass")
        self.project = Project.objects.create(name="Project Alpha", created_by=self.user)
        self.task = Task.objects.create(project=self.project, title="Task One", created_by=self.user)

    def test_thread_requires_scope(self):
        thread = Thread(title="Needs scope")
        with self.assertRaises(ValidationError):
            thread.clean()

    def test_thread_single_scope(self):
        thread = Thread(title="Too many", project=self.project, task=self.task)
        with self.assertRaises(ValidationError):
            thread.clean()


class ThreadSerializerValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jules", password="testpass")
        self.project = Project.objects.create(name="Project Beta", created_by=self.user)
        self.task = Task.objects.create(project=self.project, title="Task Two", created_by=self.user)

    def test_thread_serializer_requires_scope(self):
        serializer = ThreadSerializer(data={"title": "No scope", "kind": "general"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("project", serializer.errors)
        self.assertIn("task", serializer.errors)

    def test_thread_serializer_rejects_both_scopes(self):
        serializer = ThreadSerializer(
            data={"title": "Both", "kind": "general", "project": self.project.id, "task": self.task.id}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("project", serializer.errors)
        self.assertIn("task", serializer.errors)
