"""
Comprehensive tests for permission classes.
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from hub.models import Message, ProjectMembership, Task, Thread
from hub.permissions import (
    CanAdminProject,
    CanDeleteProject,
    CanEditProject,
    CanViewProject,
    HasProjectPermission,
    IsProjectMemberOrReadOnly,
    filter_by_project_membership,
    filter_projects_by_membership,
    user_can_access_project,
    user_can_edit_project,
)

from .factories import (
    MessageFactory,
    ProjectFactory,
    ProjectMembershipFactory,
    TaskFactory,
    ThreadFactory,
    UserFactory,
)


class HasProjectPermissionTests(TestCase):
    """Tests for base HasProjectPermission class."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = HasProjectPermission()
        self.user = UserFactory()
        self.project = ProjectFactory()

    def test_has_permission_authenticated(self):
        """Test authenticated users pass initial permission check."""
        request = self.factory.get("/")
        request.user = self.user
        self.assertTrue(self.permission.has_permission(request, None))

    def test_has_permission_unauthenticated(self):
        """Test unauthenticated users fail permission check."""
        request = self.factory.get("/")
        request.user = None
        self.assertFalse(self.permission.has_permission(request, None))

    def test_get_project_from_project(self):
        """Test extracting project from Project instance."""
        extracted = self.permission.get_project_from_obj(self.project)
        self.assertEqual(extracted, self.project)

    def test_get_project_from_task(self):
        """Test extracting project from Task instance."""
        task = TaskFactory(project=self.project)
        extracted = self.permission.get_project_from_obj(task)
        self.assertEqual(extracted, self.project)

    def test_get_project_from_thread_with_project(self):
        """Test extracting project from Thread attached to project."""
        thread = ThreadFactory(project=self.project, task=None)
        extracted = self.permission.get_project_from_obj(thread)
        self.assertEqual(extracted, self.project)

    def test_get_project_from_thread_with_task(self):
        """Test extracting project from Thread attached to task."""
        task = TaskFactory(project=self.project)
        thread = ThreadFactory(project=None, task=task)
        extracted = self.permission.get_project_from_obj(thread)
        self.assertEqual(extracted, self.project)

    def test_get_project_from_message(self):
        """Test extracting project from Message instance."""
        thread = ThreadFactory(project=self.project, task=None)
        message = MessageFactory(thread=thread)
        extracted = self.permission.get_project_from_obj(message)
        self.assertEqual(extracted, self.project)

    def test_get_user_role_in_project_with_membership(self):
        """Test getting user role when they have membership."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.ADMIN
        )
        role = self.permission.get_user_role_in_project(self.user, self.project)
        self.assertEqual(role, ProjectMembership.Role.ADMIN)

    def test_get_user_role_in_project_without_membership(self):
        """Test getting user role when they have no membership."""
        role = self.permission.get_user_role_in_project(self.user, self.project)
        self.assertIsNone(role)

    def test_has_object_permission_with_membership(self):
        """Test object permission granted with any membership."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.get("/")
        request.user = self.user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_has_object_permission_without_membership(self):
        """Test object permission denied without membership."""
        request = self.factory.get("/")
        request.user = self.user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_has_object_permission_superuser(self):
        """Test superuser bypasses all checks."""
        superuser = UserFactory(is_superuser=True)
        request = self.factory.get("/")
        request.user = superuser
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))


class CanViewProjectTests(TestCase):
    """Tests for CanViewProject permission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = CanViewProject()
        self.project = ProjectFactory()

    def test_viewer_can_view(self):
        """Test VIEWER role can view project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.get("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_member_can_view(self):
        """Test MEMBER role can view project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.MEMBER
        )
        request = self.factory.get("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_admin_can_view(self):
        """Test ADMIN role can view project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.ADMIN
        )
        request = self.factory.get("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_owner_can_view(self):
        """Test OWNER role can view project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.OWNER
        )
        request = self.factory.get("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_non_member_cannot_view(self):
        """Test non-member cannot view project."""
        user = UserFactory()
        request = self.factory.get("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_superuser_can_view(self):
        """Test superuser can view any project."""
        superuser = UserFactory(is_superuser=True)
        request = self.factory.get("/")
        request.user = superuser
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))


class CanEditProjectTests(TestCase):
    """Tests for CanEditProject permission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = CanEditProject()
        self.project = ProjectFactory()

    def test_viewer_cannot_edit(self):
        """Test VIEWER role cannot edit project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_member_can_edit(self):
        """Test MEMBER role can edit project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.MEMBER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_admin_can_edit(self):
        """Test ADMIN role can edit project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.ADMIN
        )
        request = self.factory.post("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_owner_can_edit(self):
        """Test OWNER role can edit project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.OWNER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_superuser_can_edit(self):
        """Test superuser can edit any project."""
        superuser = UserFactory(is_superuser=True)
        request = self.factory.post("/")
        request.user = superuser
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))


class CanAdminProjectTests(TestCase):
    """Tests for CanAdminProject permission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = CanAdminProject()
        self.project = ProjectFactory()

    def test_viewer_cannot_admin(self):
        """Test VIEWER role cannot admin project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_member_cannot_admin(self):
        """Test MEMBER role cannot admin project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.MEMBER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_admin_can_admin(self):
        """Test ADMIN role can admin project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.ADMIN
        )
        request = self.factory.post("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_owner_can_admin(self):
        """Test OWNER role can admin project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.OWNER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_superuser_can_admin(self):
        """Test superuser can admin any project."""
        superuser = UserFactory(is_superuser=True)
        request = self.factory.post("/")
        request.user = superuser
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))


class CanDeleteProjectTests(TestCase):
    """Tests for CanDeleteProject permission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = CanDeleteProject()
        self.project = ProjectFactory()

    def test_viewer_cannot_delete(self):
        """Test VIEWER role cannot delete project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.delete("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_member_cannot_delete(self):
        """Test MEMBER role cannot delete project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.MEMBER
        )
        request = self.factory.delete("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_admin_cannot_delete(self):
        """Test ADMIN role cannot delete project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.ADMIN
        )
        request = self.factory.delete("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_owner_can_delete(self):
        """Test OWNER role can delete project."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.OWNER
        )
        request = self.factory.delete("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_superuser_can_delete(self):
        """Test superuser can delete any project."""
        superuser = UserFactory(is_superuser=True)
        request = self.factory.delete("/")
        request.user = superuser
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))


class IsProjectMemberOrReadOnlyTests(TestCase):
    """Tests for IsProjectMemberOrReadOnly permission."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsProjectMemberOrReadOnly()
        self.project = ProjectFactory()

    def test_viewer_can_read(self):
        """Test VIEWER can perform read operations."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.get("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_viewer_cannot_write(self):
        """Test VIEWER cannot perform write operations."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.VIEWER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))

    def test_member_can_write(self):
        """Test MEMBER can perform write operations."""
        user = UserFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=user,
            role=ProjectMembership.Role.MEMBER
        )
        request = self.factory.post("/")
        request.user = user
        self.assertTrue(self.permission.has_object_permission(request, None, self.project))

    def test_non_member_cannot_read(self):
        """Test non-member cannot read."""
        user = UserFactory()
        request = self.factory.get("/")
        request.user = user
        self.assertFalse(self.permission.has_object_permission(request, None, self.project))


class HelperFunctionTests(TestCase):
    """Tests for helper functions."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()

    def test_user_can_access_project_with_membership(self):
        """Test user_can_access_project returns role when user has access."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.ADMIN
        )
        role = user_can_access_project(self.user, self.project)
        self.assertEqual(role, ProjectMembership.Role.ADMIN)

    def test_user_can_access_project_without_membership(self):
        """Test user_can_access_project returns None when user has no access."""
        role = user_can_access_project(self.user, self.project)
        self.assertIsNone(role)

    def test_user_can_access_project_superuser(self):
        """Test superuser always has OWNER access."""
        superuser = UserFactory(is_superuser=True)
        role = user_can_access_project(superuser, self.project)
        self.assertEqual(role, ProjectMembership.Role.OWNER)

    def test_user_can_edit_project_viewer(self):
        """Test VIEWER cannot edit project."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.VIEWER
        )
        self.assertFalse(user_can_edit_project(self.user, self.project))

    def test_user_can_edit_project_member(self):
        """Test MEMBER can edit project."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.MEMBER
        )
        self.assertTrue(user_can_edit_project(self.user, self.project))

    def test_user_can_edit_project_admin(self):
        """Test ADMIN can edit project."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.ADMIN
        )
        self.assertTrue(user_can_edit_project(self.user, self.project))

    def test_user_can_edit_project_owner(self):
        """Test OWNER can edit project."""
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.OWNER
        )
        self.assertTrue(user_can_edit_project(self.user, self.project))

    def test_filter_projects_by_membership(self):
        """Test filter_projects_by_membership returns only accessible projects."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        project3 = ProjectFactory()

        # User has access to project1 and project2 only
        ProjectMembershipFactory(project=project1, user=self.user)
        ProjectMembershipFactory(project=project2, user=self.user)

        from hub.models import Project
        queryset = Project.objects.all()
        filtered = filter_projects_by_membership(queryset, self.user)

        self.assertEqual(filtered.count(), 2)
        self.assertIn(project1, filtered)
        self.assertIn(project2, filtered)
        self.assertNotIn(project3, filtered)

    def test_filter_projects_by_membership_superuser(self):
        """Test superuser sees all projects."""
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()

        superuser = UserFactory(is_superuser=True)

        from hub.models import Project
        queryset = Project.objects.all()
        filtered = filter_projects_by_membership(queryset, superuser)

        self.assertEqual(filtered.count(), 3)

    def test_filter_by_project_membership_tasks(self):
        """Test filtering tasks by project membership."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        task1 = TaskFactory(project=project1)
        task2 = TaskFactory(project=project2)

        ProjectMembershipFactory(project=project1, user=self.user)

        filtered = filter_by_project_membership(Task.objects.all(), self.user)

        self.assertEqual(filtered.count(), 1)
        self.assertIn(task1, filtered)
        self.assertNotIn(task2, filtered)

    def test_filter_by_project_membership_threads(self):
        """Test filtering threads by project membership."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        thread1 = ThreadFactory(project=project1, task=None)
        thread2 = ThreadFactory(project=project2, task=None)

        ProjectMembershipFactory(project=project1, user=self.user)

        filtered = filter_by_project_membership(Thread.objects.all(), self.user)

        self.assertEqual(filtered.count(), 1)
        self.assertIn(thread1, filtered)
        self.assertNotIn(thread2, filtered)

    def test_filter_by_project_membership_superuser(self):
        """Test superuser sees all resources."""
        ProjectFactory()
        ProjectFactory()
        TaskFactory()
        TaskFactory()

        superuser = UserFactory(is_superuser=True)
        filtered = filter_by_project_membership(Task.objects.all(), superuser)

        self.assertEqual(filtered.count(), 2)
