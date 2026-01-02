"""
Comprehensive GraphQL API tests using Strawberry.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from strawberry.test import BaseGraphQLTestClient

from bothub.schema import schema
from hub.models import Message, Project, ProjectMembership, Task, Thread

from .factories import (
    MessageFactory,
    ProjectFactory,
    ProjectMembershipFactory,
    TaskFactory,
    ThreadFactory,
    UserFactory,
)

User = get_user_model()


class GraphQLTestClient(BaseGraphQLTestClient):
    """Custom GraphQL test client that handles authentication."""

    def __init__(self, request_user=None):
        super().__init__(schema)
        self.request_user = request_user

    def request(self, body, headers=None, files=None):
        # Create a mock request object with authenticated user
        from unittest.mock import Mock
        import strawberry

        request = Mock()
        request.user = self.request_user

        # Execute the GraphQL query with the schema
        result = schema.execute_sync(
            query=body.get("query"),
            variable_values=body.get("variables"),
            context_value=request,
            operation_name=body.get("operationName"),
        )

        return result


class GraphQLProjectQueryTests(TestCase):
    """Tests for Project GraphQL queries."""

    def setUp(self):
        self.user = UserFactory()
        self.client = GraphQLTestClient(request_user=self.user)

    def test_query_projects_requires_auth(self):
        """Test projects query requires authentication."""
        client = GraphQLTestClient(request_user=None)
        query = """
            query {
                projects {
                    id
                    name
                }
            }
        """
        response = client.query(query)
        self.assertIsNotNone(response.errors)

    def test_query_projects_returns_user_projects(self):
        """Test projects query returns only accessible projects."""
        project1 = ProjectFactory()
        project2 = ProjectFactory()
        ProjectFactory()  # Create a third project the user doesn't have access to

        ProjectMembershipFactory(project=project1, user=self.user)
        ProjectMembershipFactory(project=project2, user=self.user)

        query = """
            query {
                projects {
                    id
                    name
                    description
                }
            }
        """
        response = self.client.query(query)

        self.assertIsNone(response.errors)
        projects = response.data["projects"]
        self.assertEqual(len(projects), 2)
        project_ids = [int(p["id"]) for p in projects]
        self.assertIn(project1.id, project_ids)
        self.assertIn(project2.id, project_ids)

    def test_query_single_project(self):
        """Test querying a single project by ID."""
        project = ProjectFactory(name="Test Project")
        ProjectMembershipFactory(project=project, user=self.user)

        query = """
            query($id: ID!) {
                project(id: $id) {
                    id
                    name
                    description
                }
            }
        """
        response = self.client.query(query, variables={"id": project.id})

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["project"]["name"], "Test Project")

    def test_query_single_project_permission_denied(self):
        """Test querying project without access returns error."""
        project = ProjectFactory()

        query = """
            query($id: ID!) {
                project(id: $id) {
                    id
                    name
                }
            }
        """
        response = self.client.query(query, variables={"id": project.id})

        self.assertIsNotNone(response.errors)
        self.assertIn("Permission denied", str(response.errors[0].message))

    def test_query_project_with_nested_tasks(self):
        """Test querying project with nested tasks."""
        project = ProjectFactory()
        ProjectMembershipFactory(project=project, user=self.user)
        TaskFactory(project=project, title="Task 1")
        TaskFactory(project=project, title="Task 2")

        query = """
            query($id: ID!) {
                project(id: $id) {
                    id
                    name
                    tasks {
                        id
                        title
                    }
                }
            }
        """
        response = self.client.query(query, variables={"id": project.id})

        self.assertIsNone(response.errors)
        tasks = response.data["project"]["tasks"]
        self.assertEqual(len(tasks), 2)
        task_titles = [t["title"] for t in tasks]
        self.assertIn("Task 1", task_titles)
        self.assertIn("Task 2", task_titles)


class GraphQLTaskQueryTests(TestCase):
    """Tests for Task GraphQL queries."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client = GraphQLTestClient(request_user=self.user)

    def test_query_tasks_filtered_by_membership(self):
        """Test tasks query filters by project membership."""
        task1 = TaskFactory(project=self.project)
        task2 = TaskFactory(project=self.project)
        TaskFactory()  # Create a task the user doesn't have access to

        query = """
            query {
                tasks {
                    id
                    title
                }
            }
        """
        response = self.client.query(query)

        self.assertIsNone(response.errors)
        tasks = response.data["tasks"]
        task_ids = [int(t["id"]) for t in tasks]
        self.assertIn(task1.id, task_ids)
        self.assertIn(task2.id, task_ids)

    def test_query_tasks_filtered_by_project(self):
        """Test tasks query with projectId filter."""
        project2 = ProjectFactory()
        ProjectMembershipFactory(project=project2, user=self.user)

        task1 = TaskFactory(project=self.project, title="Task 1")
        TaskFactory(project=project2, title="Task 2")

        query = """
            query($projectId: ID!) {
                tasks(projectId: $projectId) {
                    id
                    title
                }
            }
        """
        response = self.client.query(query, variables={"projectId": self.project.id})

        self.assertIsNone(response.errors)
        tasks = response.data["tasks"]
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Task 1")

    def test_query_task_with_nested_relationships(self):
        """Test querying task with nested project and tags."""
        task = TaskFactory(project=self.project)

        query = """
            query {
                tasks {
                    id
                    title
                    project {
                        id
                        name
                    }
                    tags {
                        id
                        name
                    }
                }
            }
        """
        response = self.client.query(query)

        self.assertIsNone(response.errors)
        self.assertEqual(len(response.data["tasks"]), 1)
        self.assertEqual(response.data["tasks"][0]["project"]["id"], str(self.project.id))


class GraphQLThreadQueryTests(TestCase):
    """Tests for Thread GraphQL queries."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client = GraphQLTestClient(request_user=self.user)

    def test_query_threads_filtered_by_membership(self):
        """Test threads query filters by project membership."""
        thread1 = ThreadFactory(project=self.project, task=None)
        thread2 = ThreadFactory(project=self.project, task=None)
        ThreadFactory()  # Create a thread the user doesn't have access to

        query = """
            query {
                threads {
                    id
                    title
                }
            }
        """
        response = self.client.query(query)

        self.assertIsNone(response.errors)
        threads = response.data["threads"]
        thread_ids = [int(t["id"]) for t in threads]
        self.assertIn(thread1.id, thread_ids)
        self.assertIn(thread2.id, thread_ids)

    def test_query_threads_filtered_by_project(self):
        """Test threads query with projectId filter."""
        project2 = ProjectFactory()
        ProjectMembershipFactory(project=project2, user=self.user)

        thread1 = ThreadFactory(project=self.project, task=None, title="Thread 1")
        ThreadFactory(project=project2, task=None, title="Thread 2")

        query = """
            query($projectId: ID!) {
                threads(projectId: $projectId) {
                    id
                    title
                }
            }
        """
        response = self.client.query(query, variables={"projectId": self.project.id})

        self.assertIsNone(response.errors)
        threads = response.data["threads"]
        self.assertEqual(len(threads), 1)
        self.assertEqual(threads[0]["title"], "Thread 1")

    def test_query_thread_with_nested_messages(self):
        """Test querying thread with nested messages."""
        thread = ThreadFactory(project=self.project, task=None)
        MessageFactory(thread=thread, body="Message 1")
        MessageFactory(thread=thread, body="Message 2")

        query = """
            query {
                threads {
                    id
                    title
                    messages {
                        id
                        body
                    }
                }
            }
        """
        response = self.client.query(query)

        self.assertIsNone(response.errors)
        self.assertEqual(len(response.data["threads"]), 1)
        messages = response.data["threads"][0]["messages"]
        self.assertEqual(len(messages), 2)


class GraphQLMessageQueryTests(TestCase):
    """Tests for Message GraphQL queries."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.thread = ThreadFactory(project=self.project, task=None)
        self.client = GraphQLTestClient(request_user=self.user)

    def test_query_messages_filtered_by_membership(self):
        """Test messages query filters by project membership."""
        msg1 = MessageFactory(thread=self.thread)
        msg2 = MessageFactory(thread=self.thread)
        MessageFactory()  # Create a message the user doesn't have access to

        query = """
            query {
                messages {
                    id
                    body
                }
            }
        """
        response = self.client.query(query)

        self.assertIsNone(response.errors)
        messages = response.data["messages"]
        msg_ids = [int(m["id"]) for m in messages]
        self.assertIn(msg1.id, msg_ids)
        self.assertIn(msg2.id, msg_ids)

    def test_query_messages_filtered_by_thread(self):
        """Test messages query with threadId filter."""
        thread2 = ThreadFactory(project=self.project, task=None)

        msg1 = MessageFactory(thread=self.thread, body="Msg 1")
        MessageFactory(thread=thread2, body="Msg 2")

        query = """
            query($threadId: ID!) {
                messages(threadId: $threadId) {
                    id
                    body
                }
            }
        """
        response = self.client.query(query, variables={"threadId": self.thread.id})

        self.assertIsNone(response.errors)
        messages = response.data["messages"]
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]["body"], "Msg 1")


class GraphQLProjectMutationTests(TestCase):
    """Tests for Project GraphQL mutations."""

    def setUp(self):
        self.user = UserFactory()
        self.client = GraphQLTestClient(request_user=self.user)

    def test_create_project_mutation(self):
        """Test creating a project via mutation."""
        mutation = """
            mutation($input: ProjectInput!) {
                createProject(input: $input) {
                    id
                    name
                    description
                }
            }
        """
        variables = {
            "input": {
                "name": "New Project",
                "description": "Test description"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createProject"]["name"], "New Project")

        # Verify project was created
        project = Project.objects.get(name="New Project")
        self.assertEqual(project.created_by, self.user)

    def test_create_project_auto_creates_owner_membership(self):
        """Test creating project auto-creates OWNER membership."""
        mutation = """
            mutation($input: ProjectInput!) {
                createProject(input: $input) {
                    id
                    name
                }
            }
        """
        variables = {
            "input": {
                "name": "Auto Owner Project"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        project_id = int(response.data["createProject"]["id"])

        # Check OWNER membership created
        membership = ProjectMembership.objects.get(
            project_id=project_id,
            user=self.user
        )
        self.assertEqual(membership.role, ProjectMembership.Role.OWNER)

    def test_create_project_requires_auth(self):
        """Test creating project requires authentication."""
        client = GraphQLTestClient(request_user=None)

        mutation = """
            mutation($input: ProjectInput!) {
                createProject(input: $input) {
                    id
                    name
                }
            }
        """
        variables = {
            "input": {
                "name": "Unauthenticated Project"
            }
        }
        response = client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("Authentication required", str(response.errors[0].message))


class GraphQLTaskMutationTests(TestCase):
    """Tests for Task GraphQL mutations."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(
            project=self.project,
            user=self.user,
            role=ProjectMembership.Role.MEMBER
        )
        self.client = GraphQLTestClient(request_user=self.user)

    def test_create_task_mutation(self):
        """Test creating a task via mutation."""
        mutation = """
            mutation($input: TaskInput!) {
                createTask(input: $input) {
                    id
                    title
                    description
                    project {
                        id
                    }
                }
            }
        """
        variables = {
            "input": {
                "projectId": str(self.project.id),
                "title": "New Task",
                "description": "Test description"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createTask"]["title"], "New Task")

        # Verify task was created
        task = Task.objects.get(title="New Task")
        self.assertEqual(task.project, self.project)
        self.assertEqual(task.created_by, self.user)

    def test_create_task_requires_permission(self):
        """Test VIEWER cannot create tasks."""
        # Change user to VIEWER
        membership = ProjectMembership.objects.get(project=self.project, user=self.user)
        membership.role = ProjectMembership.Role.VIEWER
        membership.save()

        mutation = """
            mutation($input: TaskInput!) {
                createTask(input: $input) {
                    id
                    title
                }
            }
        """
        variables = {
            "input": {
                "projectId": str(self.project.id),
                "title": "Unauthorized Task"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("Permission denied", str(response.errors[0].message))

    def test_create_task_with_parent(self):
        """Test creating task with parent."""
        parent_task = TaskFactory(project=self.project)

        mutation = """
            mutation($input: TaskInput!) {
                createTask(input: $input) {
                    id
                    title
                    parent {
                        id
                    }
                }
            }
        """
        variables = {
            "input": {
                "projectId": str(self.project.id),
                "title": "Child Task",
                "parentId": str(parent_task.id)
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createTask"]["parent"]["id"], str(parent_task.id))

    def test_create_task_invalid_project(self):
        """Test creating task with invalid project ID."""
        mutation = """
            mutation($input: TaskInput!) {
                createTask(input: $input) {
                    id
                    title
                }
            }
        """
        variables = {
            "input": {
                "projectId": "99999",
                "title": "Invalid Project Task"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("Project not found", str(response.errors[0].message))


class GraphQLThreadMutationTests(TestCase):
    """Tests for Thread GraphQL mutations."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.client = GraphQLTestClient(request_user=self.user)

    def test_create_thread_with_project(self):
        """Test creating thread attached to project."""
        mutation = """
            mutation($input: ThreadInput!) {
                createThread(input: $input) {
                    id
                    title
                    kind
                    project {
                        id
                    }
                }
            }
        """
        variables = {
            "input": {
                "title": "New Thread",
                "kind": "planning",
                "projectId": str(self.project.id)
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createThread"]["title"], "New Thread")
        self.assertEqual(response.data["createThread"]["kind"], "planning")

    def test_create_thread_with_task(self):
        """Test creating thread attached to task."""
        task = TaskFactory(project=self.project)

        mutation = """
            mutation($input: ThreadInput!) {
                createThread(input: $input) {
                    id
                    title
                    task {
                        id
                    }
                }
            }
        """
        variables = {
            "input": {
                "title": "Task Thread",
                "taskId": str(task.id)
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createThread"]["task"]["id"], str(task.id))

    def test_create_thread_requires_scope(self):
        """Test thread creation requires project or task."""
        mutation = """
            mutation($input: ThreadInput!) {
                createThread(input: $input) {
                    id
                    title
                }
            }
        """
        variables = {
            "input": {
                "title": "No Scope Thread"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("must attach", str(response.errors[0].message))

    def test_create_thread_rejects_both_scopes(self):
        """Test thread cannot have both project and task."""
        both_scope_task = TaskFactory(project=self.project)

        mutation = """
            mutation($input: ThreadInput!) {
                createThread(input: $input) {
                    id
                    title
                }
            }
        """
        variables = {
            "input": {
                "title": "Both Scopes",
                "projectId": str(self.project.id),
                "taskId": str(both_scope_task.id)
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("one scope", str(response.errors[0].message))


class GraphQLMessageMutationTests(TestCase):
    """Tests for Message GraphQL mutations."""

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory()
        ProjectMembershipFactory(project=self.project, user=self.user)
        self.thread = ThreadFactory(project=self.project, task=None)
        self.client = GraphQLTestClient(request_user=self.user)

    def test_create_message_mutation(self):
        """Test creating a message via mutation."""
        mutation = """
            mutation($input: MessageInput!) {
                createMessage(input: $input) {
                    id
                    body
                    authorLabel
                    authorRole
                    thread {
                        id
                    }
                }
            }
        """
        variables = {
            "input": {
                "threadId": str(self.thread.id),
                "body": "Test message content"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createMessage"]["body"], "Test message content")

        # Verify message was created
        message = Message.objects.get(body="Test message content")
        self.assertEqual(message.thread, self.thread)
        self.assertEqual(message.created_by, self.user)

    def test_create_message_auto_fills_author_label(self):
        """Test author_label auto-filled from username."""
        mutation = """
            mutation($input: MessageInput!) {
                createMessage(input: $input) {
                    id
                    authorLabel
                }
            }
        """
        variables = {
            "input": {
                "threadId": str(self.thread.id),
                "body": "Auto label test"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNone(response.errors)
        self.assertEqual(response.data["createMessage"]["authorLabel"], self.user.username)

    def test_create_message_requires_permission(self):
        """Test VIEWER cannot create messages."""
        # Change user to VIEWER
        membership = ProjectMembership.objects.get(project=self.project, user=self.user)
        membership.role = ProjectMembership.Role.VIEWER
        membership.save()

        mutation = """
            mutation($input: MessageInput!) {
                createMessage(input: $input) {
                    id
                    body
                }
            }
        """
        variables = {
            "input": {
                "threadId": str(self.thread.id),
                "body": "Unauthorized message"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("Permission denied", str(response.errors[0].message))

    def test_create_message_invalid_thread(self):
        """Test creating message with invalid thread ID."""
        mutation = """
            mutation($input: MessageInput!) {
                createMessage(input: $input) {
                    id
                    body
                }
            }
        """
        variables = {
            "input": {
                "threadId": "99999",
                "body": "Invalid thread message"
            }
        }
        response = self.client.query(mutation, variables=variables)

        self.assertIsNotNone(response.errors)
        self.assertIn("Thread not found", str(response.errors[0].message))
