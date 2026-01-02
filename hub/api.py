from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets
from rest_framework.throttling import UserRateThrottle

from .audit import log_event
from .models import AuditEvent, Message, Project, ProjectMembership, Tag, Task, TaskAssignment, Thread, UserProfile, Webhook
from .permissions import (
    CanEditProject,
    CanViewProject,
    filter_by_project_membership,
    filter_projects_by_membership,
)
from .serializers import (
    AuditEventSerializer,
    MessageSerializer,
    ProjectMembershipSerializer,
    ProjectSerializer,
    TagSerializer,
    TaskAssignmentSerializer,
    TaskSerializer,
    ThreadSerializer,
    UserProfileSerializer,
    UserSerializer,
    WebhookSerializer,
)

User = get_user_model()


class AgentRateThrottle(UserRateThrottle):
    """Custom throttle that applies higher rate limits to agent users."""

    def get_rate(self):
        """Return appropriate rate based on user type."""
        from django.conf import settings

        if self.request and self.request.user and self.request.user.is_authenticated:
            profile = getattr(self.request.user, 'profile', None)
            if profile and profile.kind == 'agent':
                return settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].get('agent', '5000/hour')
        return settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].get('user', '1000/hour')


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
    throttle_classes = [AgentRateThrottle]


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.select_related("user")
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AgentRateThrottle]


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewProject]
    throttle_classes = [AgentRateThrottle]

    def get_queryset(self):
        queryset = Project.objects.all().select_related("created_by")
        return filter_projects_by_membership(queryset, self.request.user)

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        assert actor is not None, "Actor must be authenticated"
        instance = serializer.save(created_by=actor)
        # Auto-create OWNER membership for project creator
        ProjectMembership.objects.create(
            project=instance,
            user=actor,
            role=ProjectMembership.Role.OWNER,
            invited_by=actor
        )
        log_event(actor, "project.created", instance)

    def get_permissions(self):
        """Use CanEditProject for write operations."""
        if self.action in ['create', 'list']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), CanEditProject()]
        return [permissions.IsAuthenticated(), CanViewProject()]


class ProjectMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AgentRateThrottle]

    def get_queryset(self):
        """Only show memberships for projects the user has access to."""
        queryset = ProjectMembership.objects.all().select_related("project", "user", "invited_by")
        return filter_by_project_membership(queryset, self.request.user, project_field='project')

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        assert actor is not None, "Actor must be authenticated"
        instance = serializer.save(invited_by=actor)
        log_event(actor, "project.membership.created", instance)

    def get_permissions(self):
        """Use CanEditProject for write operations on project memberships."""
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), CanEditProject()]
        return [permissions.IsAuthenticated()]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AgentRateThrottle]


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewProject]
    throttle_classes = [AgentRateThrottle]

    def get_queryset(self):
        queryset = Task.objects.all().select_related("project", "parent", "created_by").prefetch_related("tags")
        # Filter by project membership
        queryset = filter_by_project_membership(queryset, self.request.user, project_field='project')
        # Apply additional filters
        project_id = parse_int(self.request.query_params.get("project"))
        parent_id = parse_int(self.request.query_params.get("parent"))
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if parent_id:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        assert actor is not None, "Actor must be authenticated"
        instance = serializer.save(created_by=actor)
        log_event(actor, "task.created", instance)

    def get_permissions(self):
        """Use CanEditProject for write operations."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), CanEditProject()]
        return [permissions.IsAuthenticated(), CanViewProject()]


class TaskAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewProject]
    throttle_classes = [AgentRateThrottle]

    def get_queryset(self):
        queryset = TaskAssignment.objects.all().select_related("task", "assignee", "added_by")
        # Filter by task's project membership
        return filter_by_project_membership(queryset, self.request.user, project_field='task__project')

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        assert actor is not None, "Actor must be authenticated"
        instance = serializer.save(added_by=actor)
        log_event(actor, "task.assignment.created", instance)

    def get_permissions(self):
        """Use CanEditProject for write operations."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), CanEditProject()]
        return [permissions.IsAuthenticated(), CanViewProject()]


class ThreadViewSet(viewsets.ModelViewSet):
    serializer_class = ThreadSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewProject]
    throttle_classes = [AgentRateThrottle]

    def get_queryset(self):
        queryset = Thread.objects.all().select_related("project", "task", "created_by")
        # Filter threads by project membership (thread can be attached to project or task)
        user = self.request.user
        if user.is_superuser:
            return queryset
        # Filter for threads attached to projects the user has access to,
        # OR threads attached to tasks whose projects the user has access to
        from django.db.models import Q
        return queryset.filter(
            Q(project__memberships__user=user) | Q(task__project__memberships__user=user)
        ).distinct()

    def perform_create(self, serializer):
        actor = get_actor(self.request)
        assert actor is not None, "Actor must be authenticated"
        instance = serializer.save(created_by=actor)
        log_event(actor, "thread.created", instance)

    def get_permissions(self):
        """Use CanEditProject for write operations."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), CanEditProject()]
        return [permissions.IsAuthenticated(), CanViewProject()]


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewProject]
    throttle_classes = [AgentRateThrottle]

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
        # Filter messages by thread's project membership
        user = self.request.user
        if not user.is_superuser:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(thread__project__memberships__user=user) | Q(thread__task__project__memberships__user=user)
            ).distinct()
        # Apply thread filter
        thread_id = parse_int(self.request.query_params.get("thread"))
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        return queryset

    def perform_create(self, serializer):
        user = get_actor(self.request)
        assert user is not None, "Actor must be authenticated"
        author_role, author_label = self._get_author_metadata(user, serializer.validated_data)
        instance = serializer.save(created_by=user, author_role=author_role, author_label=author_label)
        log_event(user, "message.created", instance)

    def get_permissions(self):
        """Use CanEditProject for write operations."""
        if self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), CanEditProject()]
        return [permissions.IsAuthenticated(), CanViewProject()]


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AgentRateThrottle]

    def get_queryset(self):
        """Filter audit events to only show those related to projects the user has access to."""
        from django.contrib.contenttypes.models import ContentType
        from django.db.models import Q

        queryset = AuditEvent.objects.all().select_related("actor", "target_content_type")
        user = self.request.user

        if user.is_superuser:
            return queryset

        # Get content types for models that are project-scoped
        project_ct = ContentType.objects.get_for_model(Project)
        task_ct = ContentType.objects.get_for_model(Task)
        thread_ct = ContentType.objects.get_for_model(Thread)
        message_ct = ContentType.objects.get_for_model(Message)
        membership_ct = ContentType.objects.get_for_model(ProjectMembership)

        # Build a filter for events related to projects the user has access to
        return queryset.filter(
            Q(target_content_type=project_ct, target_object_id__in=Project.objects.filter(memberships__user=user).values_list('id', flat=True)) |
            Q(target_content_type=task_ct, target_object_id__in=Task.objects.filter(project__memberships__user=user).values_list('id', flat=True)) |
            Q(target_content_type=thread_ct, target_object_id__in=Thread.objects.filter(
                Q(project__memberships__user=user) | Q(task__project__memberships__user=user)
            ).values_list('id', flat=True)) |
            Q(target_content_type=message_ct, target_object_id__in=Message.objects.filter(
                Q(thread__project__memberships__user=user) | Q(thread__task__project__memberships__user=user)
            ).values_list('id', flat=True)) |
            Q(target_content_type=membership_ct, target_object_id__in=ProjectMembership.objects.filter(project__memberships__user=user).values_list('id', flat=True))
        ).distinct()


class WebhookViewSet(viewsets.ModelViewSet):
    queryset = Webhook.objects.all()
    serializer_class = WebhookSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AgentRateThrottle]
