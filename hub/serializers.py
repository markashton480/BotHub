from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    AuditEvent,
    Message,
    Project,
    ProjectMembership,
    Tag,
    Task,
    TaskAssignment,
    Thread,
    UserProfile,
)

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["kind", "display_name", "notes", "created_at"]
        read_only_fields = ["created_at"]


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "profile"]
        read_only_fields = ["id", "username", "email", "profile"]


class ProjectMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMembership
        fields = ["id", "project", "user", "role", "invited_by", "created_at"]
        read_only_fields = ["invited_by", "created_at"]


class ProjectSerializer(serializers.ModelSerializer):
    user_role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "is_archived",
            "created_by",
            "created_at",
            "updated_at",
            "user_role",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at", "user_role"]

    def get_user_role(self, obj):
        """Return the requesting user's role in this project."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None

        if request.user.is_superuser:
            return ProjectMembership.Role.OWNER

        try:
            membership = ProjectMembership.objects.get(project=obj, user=request.user)
            return membership.role
        except ProjectMembership.DoesNotExist:
            return None


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug", "color", "description", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "parent",
            "title",
            "description",
            "status",
            "priority",
            "position",
            "due_at",
            "tags",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        project = attrs.get("project") or (self.instance.project if self.instance else None)
        parent = attrs.get("parent") or (self.instance.parent if self.instance else None)
        if parent and project and parent.project_id != project.id:
            raise serializers.ValidationError({"parent": "Parent task must be in the same project."})
        if self.instance and parent and parent.pk == self.instance.pk:
            raise serializers.ValidationError({"parent": "A task cannot be its own parent."})
        return attrs


class TaskAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = ["id", "task", "assignee", "role", "added_by", "created_at"]
        read_only_fields = ["added_by", "created_at"]


class ThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = [
            "id",
            "title",
            "kind",
            "project",
            "task",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_by", "created_at", "updated_at"]

    def validate(self, attrs):
        project = attrs.get("project") or (self.instance.project if self.instance else None)
        task = attrs.get("task") or (self.instance.task if self.instance else None)
        if not project and not task:
            raise serializers.ValidationError(
                {
                    "project": "Thread must be attached to a project or a task.",
                    "task": "Thread must be attached to a project or a task.",
                }
            )
        if project and task:
            raise serializers.ValidationError(
                {
                    "project": "Thread can only attach to one scope.",
                    "task": "Thread can only attach to one scope.",
                }
            )
        return attrs


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "thread",
            "created_by",
            "author_role",
            "author_label",
            "body",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["created_by", "created_at"]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "actor", "verb", "target_content_type", "target_object_id", "metadata", "created_at"]
        read_only_fields = fields
