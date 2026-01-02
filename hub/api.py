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


def get_actor(request):
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        return user
    return None


def parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        instance = serializer.save(created_by=actor)
        log_event(actor, "project.created", instance)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Task.objects.all().select_related("project", "parent", "created_by").prefetch_related("tags")
        project_id = parse_int(self.request.query_params.get("project"))
        parent_id = parse_int(self.request.query_params.get("parent"))
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        instance = serializer.save(created_by=actor)
        log_event(actor, "task.created", instance)


class TaskAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TaskAssignment.objects.all().select_related("task", "assignee", "added_by")
    serializer_class = TaskAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        instance = serializer.save(added_by=actor)
        log_event(actor, "task.assignment.created", instance)


class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all().select_related("project", "task", "created_by")
    serializer_class = ThreadSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        instance = serializer.save(created_by=actor)
        log_event(actor, "thread.created", instance)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_author_metadata(self, user, validated_data):
        author_role = validated_data.get("author_role")
        author_label = validated_data.get("author_label")
        if user:
            if not author_label:
                author_label = user.get_username()
            if not author_role:
                profile = getattr(user, "profile", None)
                if profile and profile.kind == "agent":
                    author_role = "agent"
        return author_role or "human", author_label or ""

    def get_queryset(self):
        queryset = Message.objects.all().select_related("thread", "created_by")
        thread_id = parse_int(self.request.query_params.get("thread"))
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset

    def perform_create(self, serializer):
        user = get_actor(self.request)
        author_role, author_label = self._get_author_metadata(user, serializer.validated_data)
        instance = serializer.save(created_by=user, author_role=author_role, author_label=author_label)
        log_event(user, "message.created", instance)


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.all().select_related("actor", "target_content_type")
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated]
