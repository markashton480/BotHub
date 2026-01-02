"""Custom exception classes for BotHub."""
from rest_framework import status
from rest_framework.exceptions import APIException


class ProjectNotFound(APIException):
    """Exception raised when a project is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Project not found."
    default_code = "project_not_found"


class TaskNotFound(APIException):
    """Exception raised when a task is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Task not found."
    default_code = "task_not_found"


class ThreadNotFound(APIException):
    """Exception raised when a thread is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Thread not found."
    default_code = "thread_not_found"


class MessageNotFound(APIException):
    """Exception raised when a message is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Message not found."
    default_code = "message_not_found"


class TagNotFound(APIException):
    """Exception raised when a tag is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Tag not found."
    default_code = "tag_not_found"


class InsufficientPermissions(APIException):
    """Exception raised when user lacks necessary permissions."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You don't have permission to perform this action."
    default_code = "insufficient_permissions"


class InvalidProjectMembership(APIException):
    """Exception raised when project membership configuration is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid project membership configuration."
    default_code = "invalid_membership"


class InvalidTaskAssignment(APIException):
    """Exception raised when task assignment configuration is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid task assignment configuration."
    default_code = "invalid_assignment"


# Exception registry for programmatic access
EXCEPTION_REGISTRY: dict[str, type[APIException]] = {
    ProjectNotFound.default_code: ProjectNotFound,
    TaskNotFound.default_code: TaskNotFound,
    ThreadNotFound.default_code: ThreadNotFound,
    MessageNotFound.default_code: MessageNotFound,
    TagNotFound.default_code: TagNotFound,
    InsufficientPermissions.default_code: InsufficientPermissions,
    InvalidProjectMembership.default_code: InvalidProjectMembership,
    InvalidTaskAssignment.default_code: InvalidTaskAssignment,
}


def get_exception_class(code: str) -> type[APIException] | None:
    """Return the APIException subclass registered for the given error code."""
    return EXCEPTION_REGISTRY.get(code)
