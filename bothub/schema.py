from __future__ import annotations

from typing import List, Optional

import strawberry
import strawberry_django

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from strawberry.exceptions import GraphQLError

from hub.audit import log_event
from hub.models import Message, Project, ProjectMembership, Tag, Task, TaskAssignment, Thread, UserProfile
from hub.permissions import (
    filter_by_project_membership,
    filter_projects_by_membership,
    user_can_access_project,
    user_can_edit_project,
)

User = get_user_model()


def get_actor(info):
    request = info.context
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def require_actor(info):
    actor = get_actor(info)
    if not actor:
        raise GraphQLError("Authentication required.")
    return actor


@strawberry_django.type(User, fields=["id", "username", "email"])
class UserType:
    pass


@strawberry_django.type(UserProfile, fields=["id", "kind", "display_name"])
class UserProfileType:
    pass


@strawberry_django.type(Tag)
class TagType:
    id: strawberry.auto
    name: strawberry.auto
    slug: strawberry.auto
    color: strawberry.auto
    description: strawberry.auto


@strawberry_django.type(Project)
class ProjectType:
    id: strawberry.auto
    name: strawberry.auto
    description: strawberry.auto
    is_archived: strawberry.auto
    created_at: strawberry.auto
    updated_at: strawberry.auto
    tasks: List["TaskType"]
    threads: List["ThreadType"]


@strawberry_django.type(TaskAssignment, fields=["id", "role", "created_at"])
class TaskAssignmentType:
    pass


@strawberry_django.type(Task)
class TaskType:
    id: strawberry.auto
    project: ProjectType
    parent: Optional["TaskType"]
    children: List["TaskType"]
    title: strawberry.auto
    description: strawberry.auto
    status: strawberry.auto
    priority: strawberry.auto
    position: strawberry.auto
    due_at: strawberry.auto
    tags: List[TagType]
    assignments: List[TaskAssignmentType]


@strawberry_django.type(Thread)
class ThreadType:
    id: strawberry.auto
    title: strawberry.auto
    kind: strawberry.auto
    project: Optional[ProjectType]
    task: Optional[TaskType]
    messages: List["MessageType"]


@strawberry_django.type(Message)
class MessageType:
    id: strawberry.auto
    thread: ThreadType
    created_by: Optional[UserType]
    author_role: strawberry.auto
    author_label: strawberry.auto
    body: strawberry.auto
    metadata: strawberry.auto
    created_at: strawberry.auto


@strawberry.input
class ProjectInput:
    name: str
    description: Optional[str] = ""


@strawberry.input
class TaskInput:
    project_id: strawberry.ID
    title: str
    description: Optional[str] = ""
    parent_id: Optional[strawberry.ID] = None


@strawberry.input
class ThreadInput:
    title: str
    project_id: Optional[strawberry.ID] = None
    task_id: Optional[strawberry.ID] = None
    kind: str = "general"


@strawberry.input
class MessageInput:
    thread_id: strawberry.ID
    body: str
    author_label: Optional[str] = ""
    author_role: str = "human"


@strawberry.input
class TagInput:
    name: str
    slug: str
    color: Optional[str] = "#6366f1"
    description: Optional[str] = ""


@strawberry.input
class TaskAssignmentInput:
    task_id: strawberry.ID
    assignee_id: strawberry.ID
    role: str = "assignee"


@strawberry.input
class ProjectUpdateInput:
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


@strawberry.input
class TaskUpdateInput:
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_at: Optional[str] = None
    position: Optional[int] = None


@strawberry.input
class ThreadUpdateInput:
    title: Optional[str] = None


@strawberry.input
class MessageUpdateInput:
    body: Optional[str] = None


@strawberry.input
class TagUpdateInput:
    name: Optional[str] = None
    slug: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None


@strawberry.input
class TaskAssignmentUpdateInput:
    role: Optional[str] = None


@strawberry.type
class ProjectsResult:
    """Paginated result for projects query."""
    items: List[ProjectType]
    total_count: int


@strawberry.type
class TasksResult:
    """Paginated result for tasks query."""
    items: List[TaskType]
    total_count: int


@strawberry.type
class ThreadsResult:
    """Paginated result for threads query."""
    items: List[ThreadType]
    total_count: int


@strawberry.type
class MessagesResult:
    """Paginated result for messages query."""
    items: List[MessageType]
    total_count: int


@strawberry.type
class TagsResult:
    """Paginated result for tags query."""
    items: List[TagType]
    total_count: int


@strawberry_django.type(ProjectMembership, fields=["id", "role", "created_at"])
class ProjectMembershipType:
    pass


@strawberry.type
class MembershipsResult:
    """Paginated result for memberships query."""
    items: List[ProjectMembershipType]
    total_count: int


@strawberry.type
class Query:
    @strawberry.field
    def projects(self, info, limit: int = 50, offset: int = 0) -> ProjectsResult:
        """Get paginated list of projects the user has access to."""
        actor = require_actor(info)
        if limit > 100:
            limit = 100
        queryset = Project.objects.all()
        queryset = filter_projects_by_membership(queryset, actor)
        queryset = queryset.prefetch_related('tasks', 'threads', 'memberships')
        total_count = queryset.count()
        items = list(queryset[offset:offset + limit])
        return ProjectsResult(items=items, total_count=total_count)

    @strawberry.field
    def project(self, info, id: strawberry.ID) -> Optional[ProjectType]:
        """Get a single project by ID."""
        actor = require_actor(info)
        project = Project.objects.filter(pk=id).first()
        if not project:
            return None
        # Check if user has access to this project
        if not user_can_access_project(actor, project):
            raise GraphQLError("Permission denied: You don't have access to this project.")
        return project

    @strawberry.field
    def tasks(self, info, project_id: Optional[strawberry.ID] = None, limit: int = 50, offset: int = 0) -> TasksResult:
        """Get paginated list of tasks the user has access to."""
        actor = require_actor(info)
        if limit > 100:
            limit = 100
        queryset = Task.objects.all()
        # Filter by project membership
        queryset = filter_by_project_membership(queryset, actor, project_field='project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        # Note: count() is called before slicing to provide accurate pagination metadata.
        # For large datasets, consider making total_count optional to reduce query overhead.
        total_count = queryset.count()
        items = list(queryset[offset:offset + limit])
        return TasksResult(items=items, total_count=total_count)

    @strawberry.field
    def threads(self, info, project_id: Optional[strawberry.ID] = None, limit: int = 50, offset: int = 0) -> ThreadsResult:
        """Get paginated list of threads the user has access to."""
        actor = require_actor(info)
        if limit > 100:
            limit = 100
        queryset = Thread.objects.all()
        # Filter threads by project membership (thread can be attached to project or task)
        if not actor.is_superuser:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(project__memberships__user=actor) | Q(task__project__memberships__user=actor)
            ).distinct()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        # Note: count() is called before slicing to provide accurate pagination metadata.
        # For large datasets, consider making total_count optional to reduce query overhead.
        total_count = queryset.count()
        items = list(queryset[offset:offset + limit])
        return ThreadsResult(items=items, total_count=total_count)

    @strawberry.field
    def messages(self, info, thread_id: Optional[strawberry.ID] = None, limit: int = 50, offset: int = 0) -> MessagesResult:
        """Get paginated list of messages the user has access to."""
        actor = require_actor(info)
        if limit > 100:
            limit = 100
        queryset = Message.objects.all().order_by("created_at")
        # Filter messages by thread's project membership
        if not actor.is_superuser:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(thread__project__memberships__user=actor) | Q(thread__task__project__memberships__user=actor)
            ).distinct()
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        # Note: count() is called before slicing to provide accurate pagination metadata.
        # For large datasets, consider making total_count optional to reduce query overhead.
        total_count = queryset.count()
        items = list(queryset[offset:offset + limit])
        return MessagesResult(items=items, total_count=total_count)

    @strawberry.field
    def tags(self, info, limit: int = 50, offset: int = 0) -> TagsResult:
        """Get paginated list of all tags."""
        actor = require_actor(info)
        if limit > 100:
            limit = 100
        queryset = Tag.objects.all()
        # Note: count() is called before slicing to provide accurate pagination metadata.
        # For large datasets, consider making total_count optional to reduce query overhead.
        total_count = queryset.count()
        items = list(queryset[offset:offset + limit])
        return TagsResult(items=items, total_count=total_count)

    @strawberry.field
    def memberships(self, info, project_id: Optional[strawberry.ID] = None, limit: int = 50, offset: int = 0) -> MembershipsResult:
        """Get paginated list of project memberships the user has access to."""
        actor = require_actor(info)
        if limit > 100:
            limit = 100
        queryset = ProjectMembership.objects.all().select_related("project", "user", "invited_by")
        # Only show memberships for projects the user has access to
        from .permissions import filter_by_project_membership
        queryset = filter_by_project_membership(queryset, actor, project_field='project')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        # Note: count() is called before slicing to provide accurate pagination metadata.
        # For large datasets, consider making total_count optional to reduce query overhead.
        total_count = queryset.count()
        items = list(queryset[offset:offset + limit])
        return MembershipsResult(items=items, total_count=total_count)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_project(self, info, input: ProjectInput) -> ProjectType:
        actor = require_actor(info)
        project = Project.objects.create(
            name=input.name,
            description=input.description or "",
            created_by=actor,
        )
        # Auto-create OWNER membership for project creator
        ProjectMembership.objects.create(
            project=project,
            user=actor,
            role=ProjectMembership.Role.OWNER,
            invited_by=actor
        )
        log_event(actor, "project.created", project)
        return project

    @strawberry.mutation
    def create_task(self, info, input: TaskInput) -> TaskType:
        actor = require_actor(info)
        project = Project.objects.filter(pk=input.project_id).first()
        if not project:
            raise GraphQLError("Project not found.")
        # Check if user has permission to edit this project
        if not user_can_edit_project(actor, project):
            raise GraphQLError("Permission denied: You don't have permission to create tasks in this project.")
        parent = None
        if input.parent_id:
            parent = Task.objects.filter(pk=input.parent_id).first()
            if not parent:
                raise GraphQLError("Parent task not found.")
        task = Task.objects.create(
            project=project,
            parent=parent,
            title=input.title,
            description=input.description or "",
            created_by=actor,
        )
        log_event(actor, "task.created", task)
        return task

    @strawberry.mutation
    def create_thread(self, info, input: ThreadInput) -> ThreadType:
        actor = require_actor(info)
        project = Project.objects.filter(pk=input.project_id).first() if input.project_id else None
        task = Task.objects.filter(pk=input.task_id).first() if input.task_id else None
        if input.project_id and not project:
            raise GraphQLError("Project not found.")
        if input.task_id and not task:
            raise GraphQLError("Task not found.")
        if not project and not task:
            raise GraphQLError("Thread must attach to a project or task.")
        if project and task:
            raise GraphQLError("Thread can only attach to one scope.")
        # Check permissions on the target project
        target_project = project if project else (task.project if task else None)
        if target_project and not user_can_edit_project(actor, target_project):
            raise GraphQLError("Permission denied: You don't have permission to create threads in this project.")
        thread = Thread.objects.create(
            title=input.title,
            kind=input.kind,
            project=project,
            task=task,
            created_by=actor,
        )
        log_event(actor, "thread.created", thread)
        return thread

    @strawberry.mutation
    def create_message(self, info, input: MessageInput) -> MessageType:
        """Create a new message in a thread."""
        actor = require_actor(info)
        thread = Thread.objects.filter(pk=input.thread_id).first()
        if not thread:
            raise GraphQLError("Thread not found.")
        # Check permissions on the thread's project
        target_project = thread.project if thread.project else (thread.task.project if thread.task else None)
        if target_project and not user_can_edit_project(actor, target_project):
            raise GraphQLError("Permission denied: You don't have permission to create messages in this thread.")
        message = Message.objects.create(
            thread=thread,
            body=input.body,
            author_label=input.author_label or (actor.get_username() if actor else ""),
            author_role=input.author_role,
            created_by=actor,
        )
        log_event(actor, "message.created", message)
        return message

    @strawberry.mutation
    def create_tag(self, info, input: TagInput) -> TagType:
        """Create a new tag."""
        actor = require_actor(info)
        tag = Tag.objects.create(
            name=input.name,
            slug=input.slug,
            color=input.color or "#6366f1",
            description=input.description or "",
        )
        log_event(actor, "tag.created", tag)
        return tag

    @strawberry.mutation
    def create_task_assignment(self, info, input: TaskAssignmentInput) -> TaskAssignmentType:
        """Create a new task assignment."""
        actor = require_actor(info)
        task = Task.objects.filter(pk=input.task_id).first()
        if not task:
            raise GraphQLError("Task not found.")
        # Check if user has permission to edit this task's project
        if not user_can_edit_project(actor, task.project):
            raise GraphQLError("Permission denied: You don't have permission to assign users to this task.")
        assignee = User.objects.filter(pk=input.assignee_id).first()
        if not assignee:
            raise GraphQLError("Assignee not found.")
        # Check for existing assignment to avoid IntegrityError
        if TaskAssignment.objects.filter(task=task, assignee=assignee, role=input.role).exists():
            raise GraphQLError("This assignment already exists.")
        try:
            assignment = TaskAssignment.objects.create(
                task=task,
                assignee=assignee,
                role=input.role,
                added_by=actor,
            )
        except IntegrityError:
            raise GraphQLError("This assignment already exists.")
        log_event(actor, "task.assignment.created", assignment)
        return assignment

    @strawberry.mutation
    def update_project(self, info, id: strawberry.ID, input: ProjectUpdateInput) -> ProjectType:
        """Update an existing project."""
        actor = require_actor(info)
        project = Project.objects.filter(pk=id).first()
        if not project:
            raise GraphQLError("Project not found.")
        # Check if user has permission to edit this project
        if not user_can_edit_project(actor, project):
            raise GraphQLError("Permission denied: You don't have permission to edit this project.")
        if input.name is not None:
            project.name = input.name
        if input.description is not None:
            project.description = input.description
        if input.is_archived is not None:
            project.is_archived = input.is_archived
        project.save()
        log_event(actor, "project.updated", project)
        return project

    @strawberry.mutation
    def update_task(self, info, id: strawberry.ID, input: TaskUpdateInput) -> TaskType:
        """Update an existing task."""
        actor = require_actor(info)
        task = Task.objects.filter(pk=id).first()
        if not task:
            raise GraphQLError("Task not found.")
        # Check if user has permission to edit this task's project
        if not user_can_edit_project(actor, task.project):
            raise GraphQLError("Permission denied: You don't have permission to edit this task.")
        if input.title is not None:
            task.title = input.title
        if input.description is not None:
            task.description = input.description
        if input.status is not None:
            task.status = input.status
        if input.priority is not None:
            task.priority = input.priority
        if input.due_at is not None:
            task.due_at = input.due_at
        if input.position is not None:
            task.position = input.position
        task.save()
        log_event(actor, "task.updated", task)
        return task

    @strawberry.mutation
    def update_thread(self, info, id: strawberry.ID, input: ThreadUpdateInput) -> ThreadType:
        """Update an existing thread."""
        actor = require_actor(info)
        thread = Thread.objects.filter(pk=id).first()
        if not thread:
            raise GraphQLError("Thread not found.")
        # Check permissions on the thread's project
        target_project = thread.project if thread.project else (thread.task.project if thread.task else None)
        if target_project and not user_can_edit_project(actor, target_project):
            raise GraphQLError("Permission denied: You don't have permission to edit this thread.")
        if input.title is not None:
            thread.title = input.title
        thread.save()
        log_event(actor, "thread.updated", thread)
        return thread

    @strawberry.mutation
    def update_message(self, info, id: strawberry.ID, input: MessageUpdateInput) -> MessageType:
        """Update an existing message."""
        actor = require_actor(info)
        message = Message.objects.filter(pk=id).first()
        if not message:
            raise GraphQLError("Message not found.")
        # Check permissions on the message's thread's project
        target_project = message.thread.project if message.thread.project else (message.thread.task.project if message.thread.task else None)
        if target_project and not user_can_edit_project(actor, target_project):
            raise GraphQLError("Permission denied: You don't have permission to edit this message.")
        if input.body is not None:
            message.body = input.body
        message.save()
        log_event(actor, "message.updated", message)
        return message

    @strawberry.mutation
    def update_tag(self, info, id: strawberry.ID, input: TagUpdateInput) -> TagType:
        """Update an existing tag."""
        actor = require_actor(info)
        tag = Tag.objects.filter(pk=id).first()
        if not tag:
            raise GraphQLError("Tag not found.")
        if input.name is not None:
            tag.name = input.name
        if input.slug is not None:
            tag.slug = input.slug
        if input.color is not None:
            tag.color = input.color
        if input.description is not None:
            tag.description = input.description
        tag.save()
        log_event(actor, "tag.updated", tag)
        return tag

    @strawberry.mutation
    def update_task_assignment(self, info, id: strawberry.ID, input: TaskAssignmentUpdateInput) -> TaskAssignmentType:
        """Update an existing task assignment."""
        actor = require_actor(info)
        assignment = TaskAssignment.objects.filter(pk=id).first()
        if not assignment:
            raise GraphQLError("Task assignment not found.")
        # Check if user has permission to edit this assignment's task's project
        if not user_can_edit_project(actor, assignment.task.project):
            raise GraphQLError("Permission denied: You don't have permission to edit this assignment.")
        if input.role is not None:
            assignment.role = input.role
        assignment.save()
        log_event(actor, "task.assignment.updated", assignment)
        return assignment

    @strawberry.mutation
    def delete_project(self, info, id: strawberry.ID) -> bool:
        """Delete a project."""
        actor = require_actor(info)
        project = Project.objects.filter(pk=id).first()
        if not project:
            raise GraphQLError("Project not found.")
        # Check if user has permission to edit this project (owners can delete)
        if not user_can_edit_project(actor, project):
            raise GraphQLError("Permission denied: You don't have permission to delete this project.")
        log_event(actor, "project.deleted", project)
        project.delete()
        return True

    @strawberry.mutation
    def delete_task(self, info, id: strawberry.ID) -> bool:
        """Delete a task."""
        actor = require_actor(info)
        task = Task.objects.filter(pk=id).first()
        if not task:
            raise GraphQLError("Task not found.")
        # Check if user has permission to edit this task's project
        if not user_can_edit_project(actor, task.project):
            raise GraphQLError("Permission denied: You don't have permission to delete this task.")
        log_event(actor, "task.deleted", task)
        task.delete()
        return True

    @strawberry.mutation
    def delete_thread(self, info, id: strawberry.ID) -> bool:
        """Delete a thread."""
        actor = require_actor(info)
        thread = Thread.objects.filter(pk=id).first()
        if not thread:
            raise GraphQLError("Thread not found.")
        # Check permissions on the thread's project
        target_project = thread.project if thread.project else (thread.task.project if thread.task else None)
        if target_project and not user_can_edit_project(actor, target_project):
            raise GraphQLError("Permission denied: You don't have permission to delete this thread.")
        log_event(actor, "thread.deleted", thread)
        thread.delete()
        return True

    @strawberry.mutation
    def delete_message(self, info, id: strawberry.ID) -> bool:
        """Delete a message."""
        actor = require_actor(info)
        message = Message.objects.filter(pk=id).first()
        if not message:
            raise GraphQLError("Message not found.")
        # Check permissions on the message's thread's project
        target_project = message.thread.project if message.thread.project else (message.thread.task.project if message.thread.task else None)
        if target_project and not user_can_edit_project(actor, target_project):
            raise GraphQLError("Permission denied: You don't have permission to delete this message.")
        log_event(actor, "message.deleted", message)
        message.delete()
        return True

    @strawberry.mutation
    def delete_tag(self, info, id: strawberry.ID) -> bool:
        """Delete a tag."""
        actor = require_actor(info)
        tag = Tag.objects.filter(pk=id).first()
        if not tag:
            raise GraphQLError("Tag not found.")
        log_event(actor, "tag.deleted", tag)
        tag.delete()
        return True

    @strawberry.mutation
    def delete_task_assignment(self, info, id: strawberry.ID) -> bool:
        """Delete a task assignment."""
        actor = require_actor(info)
        assignment = TaskAssignment.objects.filter(pk=id).first()
        if not assignment:
            raise GraphQLError("Task assignment not found.")
        # Check if user has permission to edit this assignment's task's project
        if not user_can_edit_project(actor, assignment.task.project):
            raise GraphQLError("Permission denied: You don't have permission to delete this assignment.")
        log_event(actor, "task.assignment.deleted", assignment)
        assignment.delete()
        return True


schema = strawberry.Schema(query=Query, mutation=Mutation)
