from django.urls import path

from . import views

app_name = "hub"

urlpatterns = [
    path("", views.home, name="home"),
    path("projects/create/", views.project_create, name="project-create"),
    path("projects/<int:project_id>/", views.project_detail, name="project-detail"),
    path("projects/<int:project_id>/tasks/create/", views.task_create, name="task-create"),
    path("projects/<int:project_id>/threads/create/", views.thread_create, name="thread-create"),
    path("threads/<int:thread_id>/", views.thread_detail, name="thread-detail"),
    path("threads/<int:thread_id>/messages/create/", views.message_create, name="message-create"),
]
