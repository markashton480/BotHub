"""Simple test factories."""
import factory
from django.contrib.auth import get_user_model
from hub.models import Project, ProjectMembership, Task, Thread, Message, Tag, UserProfile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@test.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    kind = "human"


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f"Project {n}")
    created_by = factory.SubFactory(UserFactory)


class ProjectMembershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProjectMembership

    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)
    role = ProjectMembership.Role.MEMBER
    invited_by = factory.LazyAttribute(lambda o: o.project.created_by)


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"tag-{n}")
    slug = factory.Sequence(lambda n: f"tag-{n}")


class TaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Task

    project = factory.SubFactory(ProjectFactory)
    title = factory.Sequence(lambda n: f"Task {n}")
    created_by = factory.SubFactory(UserFactory)


class ThreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Thread

    project = factory.SubFactory(ProjectFactory)
    task = None
    title = factory.Sequence(lambda n: f"Thread {n}")
    created_by = factory.SubFactory(UserFactory)


class MessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Message

    thread = factory.SubFactory(ThreadFactory)
    body = factory.Sequence(lambda n: f"Message body {n}")
    author_label = "test_user"
    author_role = Message.AuthorRole.HUMAN
    created_by = factory.SubFactory(UserFactory)
