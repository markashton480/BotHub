from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .audit import log_event
from .forms import MessageForm, ProjectForm, TaskForm, ThreadForm
from .models import Message, Project, Task, Thread


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


def home(request):
    projects = Project.objects.all().order_by("name")
    return render(
        request,
        "hub/home.html",
        {
            "projects": projects,
            "project_form": ProjectForm(),
        },
    )


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
    project.created_by = request.user if request.user.is_authenticated else None
    project.save()
    log_event(project.created_by, "project.created", project)
    if request.htmx:
        return render(request, "hub/partials/project_row.html", {"project": project})
    return redirect("hub:home")


def project_detail(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
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


def task_create(request, project_id):
    if request.method != "POST":
        return redirect("hub:project-detail", project_id=project_id)
    project = get_object_or_404(Project, pk=project_id)
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
    task.created_by = request.user if request.user.is_authenticated else None
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


def thread_create(request, project_id):
    if request.method != "POST":
        return redirect("hub:project-detail", project_id=project_id)
    project = get_object_or_404(Project, pk=project_id)
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
    thread.created_by = request.user if request.user.is_authenticated else None
    thread.save()
    log_event(thread.created_by, "thread.created", thread)
    if request.htmx:
        thread.message_count = 0
        return render(request, "hub/partials/thread_row.html", {"thread": thread})
    return redirect("hub:project-detail", project_id=project_id)


def thread_detail(request, thread_id):
    thread = get_object_or_404(Thread, pk=thread_id)
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


def message_create(request, thread_id):
    if request.method != "POST":
        return redirect("hub:thread-detail", thread_id=thread_id)
    thread = get_object_or_404(Thread, pk=thread_id)
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
    message.created_by = request.user if request.user.is_authenticated else None
    if message.created_by and not message.author_label:
        message.author_label = message.created_by.get_username()
    message.save()
    log_event(message.created_by, "message.created", message)
    if request.htmx:
        return render(request, "hub/partials/message_row.html", {"message": message})
    return redirect("hub:thread-detail", thread_id=thread_id)
