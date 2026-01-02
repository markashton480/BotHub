"""
Permission classes for row-level access control based on ProjectMembership.

All resources (Projects, Tasks, Threads, Messages) are scoped by project membership,
and users must have appropriate membership to access related resources.
"""
from rest_framework import permissions
from .models import ProjectMembership, Project, Task, Thread


class HasProjectPermission(permissions.BasePermission):
    """
    Base permission class for project-scoped resources.
    Checks if user has any membership in the relevant project.
    """

    def has_permission(self, request, view):
        """Allow authenticated users to proceed to object-level checks."""
        return request.user and request.user.is_authenticated

    def get_project_from_obj(self, obj):
        """Extract the project from a model instance. Override in subclasses if needed."""
        if isinstance(obj, Project):
            return obj
        elif isinstance(obj, Task):
            return obj.project
        elif isinstance(obj, Thread):
            # Thread can be attached to project or task
            return obj.project if obj.project else (obj.task.project if obj.task else None)
        elif hasattr(obj, 'thread'):
            # Message
            thread = obj.thread
            return thread.project if thread.project else (thread.task.project if thread.task else None)
        return None

    def get_user_role_in_project(self, user, project):
        """Get user's role in a project, or None if not a member."""
        if not project:
            return None
        try:
            membership = ProjectMembership.objects.get(project=project, user=user)
            return membership.role
        except ProjectMembership.DoesNotExist:
            return None

    def has_object_permission(self, request, view, obj):
        """Check if user has permission for this specific object."""
        # Superusers bypass all checks
        if request.user.is_superuser:
            return True

        project = self.get_project_from_obj(obj)
        if not project:
            return False

        role = self.get_user_role_in_project(request.user, project)
        return role is not None  # Has any membership


class CanViewProject(HasProjectPermission):
    """
    Permission for viewing projects and their resources.
    All roles (VIEWER, MEMBER, ADMIN, OWNER) can view.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project_from_obj(obj)
        if not project:
            return False

        role = self.get_user_role_in_project(request.user, project)
        # All roles can view - any membership grants view access
        return role is not None


class CanEditProject(HasProjectPermission):
    """
    Permission for editing projects and their resources.
    MEMBER, ADMIN, and OWNER can edit.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project_from_obj(obj)
        if not project:
            return False

        role = self.get_user_role_in_project(request.user, project)
        # MEMBER+ can edit
        return role in [
            ProjectMembership.Role.MEMBER,
            ProjectMembership.Role.ADMIN,
            ProjectMembership.Role.OWNER,
        ]


class CanAdminProject(HasProjectPermission):
    """
    Permission for administrative actions (managing members, settings).
    ADMIN and OWNER can perform admin actions.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project_from_obj(obj)
        if not project:
            return False

        role = self.get_user_role_in_project(request.user, project)
        # ADMIN+ can admin
        return role in [
            ProjectMembership.Role.ADMIN,
            ProjectMembership.Role.OWNER,
        ]


class CanDeleteProject(HasProjectPermission):
    """
    Permission for deleting projects.
    Only OWNER can delete.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project_from_obj(obj)
        if not project:
            return False

        role = self.get_user_role_in_project(request.user, project)
        # Only OWNER can delete
        return role == ProjectMembership.Role.OWNER


class IsProjectMemberOrReadOnly(HasProjectPermission):
    """
    Permission that allows read access to members and write access to MEMBER+.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        project = self.get_project_from_obj(obj)
        if not project:
            return False

        role = self.get_user_role_in_project(request.user, project)
        if not role:
            return False

        # Read-only access for VIEWER
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write access for MEMBER+
        return role in [
            ProjectMembership.Role.MEMBER,
            ProjectMembership.Role.ADMIN,
            ProjectMembership.Role.OWNER,
        ]


def user_can_access_project(user, project):
    """
    Helper function to check if a user can access a project.
    Returns the user's role if they have access, None otherwise.
    """
    if user.is_superuser:
        return ProjectMembership.Role.OWNER

    try:
        membership = ProjectMembership.objects.get(project=project, user=user)
        return membership.role
    except ProjectMembership.DoesNotExist:
        return None


def user_can_edit_project(user, project):
    """
    Helper function to check if a user can edit a project.
    Returns True if user has MEMBER+ role.
    """
    role = user_can_access_project(user, project)
    return role in [
        ProjectMembership.Role.MEMBER,
        ProjectMembership.Role.ADMIN,
        ProjectMembership.Role.OWNER,
    ]


def filter_projects_by_membership(queryset, user):
    """
    Filter a Project queryset to only include projects the user has access to.
    """
    if user.is_superuser:
        return queryset
    return queryset.filter(memberships__user=user).distinct()


def filter_by_project_membership(queryset, user, project_field='project'):
    """
    Filter any queryset by project membership.
    Works for Task, Thread, Message by following the project relationship.
    """
    if user.is_superuser:
        return queryset

    # Build the filter path to the project's memberships
    filter_kwargs = {f'{project_field}__memberships__user': user}
    return queryset.filter(**filter_kwargs).distinct()
