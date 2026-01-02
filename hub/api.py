from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets

from .audit import log_event
from .models import AuditEvent, Message, Project, Tag, Task, TaskAssignment, Thread, UserProfile
from .serializers import (
    AuditEventSerializer,
    MessageSerializer,
    ProjectSerializer,
    TagSerializer,
    TaskAssignmentSerializer,
    TaskSerializer,
    ThreadSerializer,
    UserProfileSerializer,
    UserSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().select_related("profile")
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.select_related("user")
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all().select_related("created_by")
    serializer_class = ProjectSerializer

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=actor)
        log_event(actor, "project.created", instance)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        queryset = Task.objects.all().select_related("project", "parent", "created_by").prefetch_related("tags")
        project_id = self.request.query_params.get("project")
        parent_id = self.request.query_params.get("parent")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=actor)
        log_event(actor, "task.created", instance)


class TaskAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TaskAssignment.objects.all().select_related("task", "assignee", "added_by")
    serializer_class = TaskAssignmentSerializer

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(added_by=actor)
        log_event(actor, "task.assignment.created", instance)


class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all().select_related("project", "task", "created_by")
    serializer_class = ThreadSerializer

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        instance = serializer.save(created_by=actor)
        log_event(actor, "thread.created", instance)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer

    def get_queryset(self):
        queryset = Message.objects.all().select_related("thread", "created_by")
        thread_id = self.request.query_params.get("thread")
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        author_role = serializer.validated_data.get("author_role")
        author_label = serializer.validated_data.get("author_label")
        if user and not author_label:
            author_label = user.get_username()
        if user and not author_role:
            profile = getattr(user, "profile", None)
            if profile and profile.kind == "agent":
                author_role = "agent"
        instance = serializer.save(
            created_by=user, author_role=author_role or "human", author_label=author_label or ""
        )
        log_event(user, "message.created", instance)


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.all().select_related("actor", "target_content_type")
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated]
