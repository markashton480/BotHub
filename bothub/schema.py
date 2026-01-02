from __future__ import annotations

from typing import List, Optional

import strawberry
import strawberry_django

from django.contrib.auth import get_user_model

from hub.audit import log_event
from hub.models import Message, Project, Tag, Task, Thread, UserProfile

User = get_user_model()


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


@strawberry.type
class Query:
    @strawberry.field
    def projects(self) -> List[ProjectType]:
        return Project.objects.all()

    @strawberry.field
    def project(self, id: strawberry.ID) -> Optional[ProjectType]:
        return Project.objects.filter(pk=id).first()

    @strawberry.field
    def tasks(self, project_id: Optional[strawberry.ID] = None) -> List[TaskType]:
        queryset = Task.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return list(queryset)

    @strawberry.field
    def threads(self, project_id: Optional[strawberry.ID] = None) -> List[ThreadType]:
        queryset = Thread.objects.all()
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return list(queryset)

    @strawberry.field
    def messages(self, thread_id: Optional[strawberry.ID] = None) -> List[MessageType]:
        queryset = Message.objects.all().order_by("created_at")
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return list(queryset)


@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_project(self, info, input: ProjectInput) -> ProjectType:
        request = info.context
        user = getattr(request, "user", None)
        project = Project.objects.create(
            name=input.name,
            description=input.description or "",
            created_by=user if user and user.is_authenticated else None,
        )
        log_event(user if user and user.is_authenticated else None, "project.created", project)
        return project

    @strawberry.mutation
    def create_task(self, info, input: TaskInput) -> TaskType:
        request = info.context
        user = getattr(request, "user", None)
        project = Project.objects.get(pk=input.project_id)
        parent = Task.objects.filter(pk=input.parent_id).first() if input.parent_id else None
        task = Task.objects.create(
            project=project,
            parent=parent,
            title=input.title,
            description=input.description or "",
            created_by=user if user and user.is_authenticated else None,
        )
        log_event(user if user and user.is_authenticated else None, "task.created", task)
        return task

    @strawberry.mutation
    def create_thread(self, info, input: ThreadInput) -> ThreadType:
        request = info.context
        user = getattr(request, "user", None)
        project = Project.objects.filter(pk=input.project_id).first() if input.project_id else None
        task = Task.objects.filter(pk=input.task_id).first() if input.task_id else None
        if not project and not task:
            raise ValueError("Thread must attach to a project or task.")
        if project and task:
            raise ValueError("Thread can only attach to one scope.")
        thread = Thread.objects.create(
            title=input.title,
            kind=input.kind,
            project=project,
            task=task,
            created_by=user if user and user.is_authenticated else None,
        )
        log_event(user if user and user.is_authenticated else None, "thread.created", thread)
        return thread

    @strawberry.mutation
    def create_message(self, info, input: MessageInput) -> MessageType:
        request = info.context
        user = getattr(request, "user", None)
        thread = Thread.objects.get(pk=input.thread_id)
        message = Message.objects.create(
            thread=thread,
            body=input.body,
            author_label=input.author_label or (user.get_username() if user and user.is_authenticated else ""),
            author_role=input.author_role,
            created_by=user if user and user.is_authenticated else None,
        )
        log_event(user if user and user.is_authenticated else None, "message.created", message)
        return message


schema = strawberry.Schema(query=Query, mutation=Mutation)
