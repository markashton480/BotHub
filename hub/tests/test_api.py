"""API tests."""
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .factories import UserFactory, ProjectFactory, ProjectMembershipFactory, TaskFactory


class ProjectAPITests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_list_projects(self):
        project = ProjectFactory()
        ProjectMembershipFactory(project=project, user=self.user)

        response = self.client.get(reverse("project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_project(self):
        response = self.client.post(reverse("project-list"), {"name": "New Project"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Project")

    def test_unauthenticated_access_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("project-list"))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])


class TaskAPITests(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client.force_authenticate(user=self.user)

    def test_list_tasks(self):
        TaskFactory(project=self.project)
        response = self.client.get(reverse("task-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_task(self):
        response = self.client.post(reverse("task-list"), {
            "project": self.project.id,
            "title": "New Task"
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
