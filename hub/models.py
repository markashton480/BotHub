from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

User = get_user_model()


class UserProfile(models.Model):
    class Kind(models.TextChoices):
        HUMAN = "human", "Human"
        AGENT = "agent", "Agent"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.HUMAN)
    display_name = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.display_name or self.user.get_username()


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="projects_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]

    def __str__(self) -> str:
        return self.name


class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    invited_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="memberships_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["project_id", "role", "id"]

    def __str__(self) -> str:
        return f"{self.user} -> {self.project} ({self.role})"


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)
    color = models.CharField(max_length=12, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        BACKLOG = "backlog", "Backlog"
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        BLOCKED = "blocked", "Blocked"
        DONE = "done", "Done"

    class Priority(models.IntegerChoices):
        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"
        URGENT = 4, "Urgent"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BACKLOG)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    position = models.PositiveIntegerField(default=0)
    due_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="tasks")
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["project_id", "parent_id", "position", "id"]

    def clean(self) -> None:
        if self.parent_id and self.parent_id == self.id:
            raise ValidationError({"parent": "A task cannot be its own parent."})
        if self.parent_id and self.parent and self.parent.project_id != self.project_id:
            raise ValidationError({"parent": "Parent task must be in the same project."})

    def __str__(self) -> str:
        return self.title


class TaskAssignment(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ASSIGNEE = "assignee", "Assignee"
        REVIEWER = "reviewer", "Reviewer"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assignments")
    assignee = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="task_assignments"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ASSIGNEE)
    added_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assignments_added"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("task", "assignee", "role")

    def __str__(self) -> str:
        return f"{self.assignee} -> {self.task}"


class Thread(models.Model):
    class Kind(models.TextChoices):
        GENERAL = "general", "General"
        PLANNING = "planning", "Planning"
        UPDATE = "update", "Update"

    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.GENERAL)
    project = models.ForeignKey(
        Project, null=True, blank=True, on_delete=models.CASCADE, related_name="threads"
    )
    task = models.ForeignKey(
        Task, null=True, blank=True, on_delete=models.CASCADE, related_name="threads"
    )
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="threads_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(project__isnull=False) | Q(task__isnull=False),
                name="thread_requires_scope",
            ),
            models.CheckConstraint(
                check=~(Q(project__isnull=False) & Q(task__isnull=False)),
                name="thread_single_scope",
            ),
        ]

    def clean(self) -> None:
        # Keep checks here for friendly validation messages alongside DB constraints.
        if not self.project_id and not self.task_id:
            raise ValidationError("Thread must be attached to a project or a task.")
        if self.project_id and self.task_id:
            raise ValidationError("Thread can only attach to one scope.")

    def __str__(self) -> str:
        return self.title


class Message(models.Model):
    class AuthorRole(models.TextChoices):
        HUMAN = "human", "Human"
        AGENT = "agent", "Agent"
        SYSTEM = "system", "System"

    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name="messages")
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages_created"
    )
    author_role = models.CharField(
        max_length=20, choices=AuthorRole.choices, default=AuthorRole.HUMAN
    )
    author_label = models.CharField(max_length=100, blank=True)
    body = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return f"{self.thread} ({self.created_at:%Y-%m-%d})"


class AuditEvent(models.Model):
    actor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events"
    )
    verb = models.CharField(max_length=80)
    target_content_type = models.ForeignKey(
        ContentType, null=True, blank=True, on_delete=models.SET_NULL
    )
    target_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    target = GenericForeignKey("target_content_type", "target_object_id")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.verb} ({self.created_at:%Y-%m-%d %H:%M})"
