"""
Factory classes for creating test data using factory_boy.
"""
import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

from hub.models import (
    AuditEvent,
    Message,
    Project,
    ProjectMembership,
    Tag,
    Task,
    TaskAssignment,
    Thread,
    UserProfile,
    Webhook,
)

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.set_password(extracted)
        else:
            self.set_password("testpass123")


class UserProfileFactory(DjangoModelFactory):
    """Factory for creating UserProfile instances."""

    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    kind = UserProfile.Kind.HUMAN
    display_name = factory.Faker("name")
    notes = factory.Faker("text", max_nb_chars=200)


class ProjectFactory(DjangoModelFactory):
    """Factory for creating Project instances."""

    class Meta:
        model = Project

    name = factory.Faker("catch_phrase")
    description = factory.Faker("paragraph")
    is_archived = False
    created_by = factory.SubFactory(UserFactory)


class ProjectMembershipFactory(DjangoModelFactory):
    """Factory for creating ProjectMembership instances."""

    class Meta:
        model = ProjectMembership

    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = ProjectMembership.Role.MEMBER
    invited_by = factory.SubFactory(UserFactory)


class TagFactory(DjangoModelFactory):
    """Factory for creating Tag instances."""

    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"Tag-{n}")
    # slug auto-generated in model save()
    color = factory.Faker("hex_color")
    description = factory.Faker("sentence")


class TaskFactory(DjangoModelFactory):
    """Factory for creating Task instances."""

    class Meta:
        model = Task

    project = factory.SubFactory(ProjectFactory)
    parent = None
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("paragraph")
    # status defaults to Task.Status.BACKLOG from model
    priority = Task.Priority.MEDIUM
    position = 0
    due_at = None
    created_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class TaskAssignmentFactory(DjangoModelFactory):
    """Factory for creating TaskAssignment instances."""

    class Meta:
        model = TaskAssignment

    task = factory.SubFactory(TaskFactory)
    assignee = factory.SubFactory(UserFactory)
    role = TaskAssignment.Role.ASSIGNEE
    added_by = factory.SubFactory(UserFactory)


class ThreadFactory(DjangoModelFactory):
    """Factory for creating Thread instances."""

    class Meta:
        model = Thread

    title = factory.Faker("sentence", nb_words=4)
    kind = Thread.Kind.GENERAL
    project = factory.SubFactory(ProjectFactory)
    task = None
    created_by = factory.SubFactory(UserFactory)


class MessageFactory(DjangoModelFactory):
    """Factory for creating Message instances."""

    class Meta:
        model = Message

    thread = factory.SubFactory(ThreadFactory)
    created_by = factory.SubFactory(UserFactory)
    author_role = Message.AuthorRole.HUMAN
    author_label = factory.LazyAttribute(lambda obj: obj.created_by.username if obj.created_by else "Anonymous")
    body = factory.Faker("paragraph")
    metadata = factory.Dict({})


class WebhookFactory(DjangoModelFactory):
    """Factory for creating Webhook instances."""

    class Meta:
        model = Webhook

    name = factory.Faker("company")
    url = factory.Faker("url")
    secret = factory.Faker("password", length=32)
    events = factory.List(["project.created", "task.created"])
    is_active = True


class AuditEventFactory(DjangoModelFactory):
    """Factory for creating AuditEvent instances."""

    class Meta:
        model = AuditEvent

    actor = factory.SubFactory(UserFactory)
    verb = "test.action"
    target_content_type = None
    target_object_id = None
    metadata = factory.Dict({})
