from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .audit import log_event
from .forms import MessageForm, ProjectForm, TaskForm, ThreadForm
from .models import Message, Project, ProjectMembership, Task, Thread
from .permissions import (
    filter_projects_by_membership,
    user_can_access_project,
    user_can_edit_project,
)


def build_task_tree(tasks):
    nodes = {task.id: {"task": task, "children": []} for task in tasks}
    roots = []
    for task in tasks:
        node = nodes[task.id]
        if task.parent_id and task.parent_id in nodes:
            nodes[task.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def get_project_tasks(project):
    return (
        Task.objects.filter(project=project)
        .select_related("parent")
        .order_by("parent_id", "position", "id")
    )


def htmx_form_error(request, template_name, context, target_id):
    response = render(request, template_name, context, status=400)
    if request.htmx:
        response["HX-Retarget"] = target_id
        response["HX-Reswap"] = "innerHTML"
    return response


@login_required
def home(request):
    projects = Project.objects.all().order_by("name")
    # Filter projects by membership
    projects = filter_projects_by_membership(projects, request.user)
    return render(
        request,
        "hub/home.html",
        {
            "projects": projects,
            "project_form": ProjectForm(),
        },
    )


@login_required
def project_create(request):
    if request.method != "POST":
        return redirect("hub:home")
    form = ProjectForm(request.POST)
    if not form.is_valid():
        return htmx_form_error(
            request,
            "hub/partials/project_form.html",
            {"project_form": form},
            "#project-form",
        )
    project = form.save(commit=False)
    project.created_by = request.user
    project.save()
    # Auto-create OWNER membership for project creator
    ProjectMembership.objects.create(
        project=project,
        user=request.user,
        role=ProjectMembership.Role.OWNER,
        invited_by=request.user
    )
    log_event(project.created_by, "project.created", project)
    if request.htmx:
        return render(request, "hub/partials/project_row.html", {"project": project})
    return redirect("hub:home")


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    # Check if user has access to this project
    if not user_can_access_project(request.user, project):
        raise PermissionDenied("You don't have access to this project.")
    tasks = get_project_tasks(project)
    task_tree = build_task_tree(tasks)
    threads = (
        Thread.objects.filter(project=project)
        .annotate(message_count=Count("messages"))
        .order_by("-updated_at")
    )
    return render(
        request,
        "hub/project_detail.html",
        {
            "project": project,
            "task_tree": task_tree,
            "threads": threads,
            "task_form": TaskForm(project=project),
            "thread_form": ThreadForm(),
        },
    )


@login_required
def task_create(request, project_id):
    if request.method != "POST":
        return redirect("hub:project-detail", project_id=project_id)
    project = get_object_or_404(Project, pk=project_id)
    # Check if user has permission to edit this project
    if not user_can_edit_project(request.user, project):
        raise PermissionDenied("You don't have permission to create tasks in this project.")
    form = TaskForm(request.POST, project=project)
    if not form.is_valid():
        return htmx_form_error(
            request,
            "hub/partials/task_form.html",
            {"task_form": form, "project": project},
            "#task-form",
        )
    task = form.save(commit=False)
    task.project = project
    task.created_by = request.user
    task.save()
    form.save_m2m()
    log_event(task.created_by, "task.created", task)
    if request.htmx:
        tasks = get_project_tasks(project)
        return render(
            request,
            "hub/partials/task_tree.html",
            {"task_tree": build_task_tree(tasks)},
        )
    return redirect("hub:project-detail", project_id=project_id)


@login_required
def thread_create(request, project_id):
    if request.method != "POST":
        return redirect("hub:project-detail", project_id=project_id)
    project = get_object_or_404(Project, pk=project_id)
    # Check if user has permission to edit this project
    if not user_can_edit_project(request.user, project):
        raise PermissionDenied("You don't have permission to create threads in this project.")
    form = ThreadForm(request.POST)
    if not form.is_valid():
        return htmx_form_error(
            request,
            "hub/partials/thread_form.html",
            {"thread_form": form, "project": project},
            "#thread-form",
        )
    thread = form.save(commit=False)
    thread.project = project
    thread.created_by = request.user
    thread.save()
    log_event(thread.created_by, "thread.created", thread)
    if request.htmx:
        thread.message_count = 0
        return render(request, "hub/partials/thread_row.html", {"thread": thread})
    return redirect("hub:project-detail", project_id=project_id)


@login_required
def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
    # Check if user has access to this thread's project
    target_project = thread.project if thread.project else (thread.task.project if thread.task else None)
    if target_project and not user_can_access_project(request.user, target_project):
        raise PermissionDenied("You don't have access to this thread.")
    messages = Message.objects.filter(thread=thread).select_related("created_by")
    return render(
        request,
        "hub/thread_detail.html",
        {
            "thread": thread,
            "messages": messages,
            "message_form": MessageForm(),
        },
    )


@login_required
def message_create(request, thread_id):
    if request.method != "POST":
        return redirect("hub:thread-detail", thread_id=thread_id)
    thread = get_object_or_404(Thread, pk=thread_id)
    # Check if user has permission to edit this thread's project
    target_project = thread.project if thread.project else (thread.task.project if thread.task else None)
    if target_project and not user_can_edit_project(request.user, target_project):
        raise PermissionDenied("You don't have permission to create messages in this thread.")
    form = MessageForm(request.POST)
    if not form.is_valid():
        return htmx_form_error(
            request,
            "hub/partials/message_form.html",
            {"message_form": form, "thread": thread},
            "#message-form",
        )
    message = form.save(commit=False)
    message.thread = thread
    message.created_by = request.user
    if not message.author_label:
        message.author_label = message.created_by.get_username()
    message.save()
    log_event(message.created_by, "message.created", message)
    if request.htmx:
        return render(request, "hub/partials/message_row.html", {"message": message})
    return redirect("hub:thread-detail", thread_id=thread_id)
