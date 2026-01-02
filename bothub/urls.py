"""
URL configuration for bothub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter
from strawberry.django.views import GraphQLView

from hub import api as hub_api
from .schema import schema

router = DefaultRouter()
router.register("users", hub_api.UserViewSet, basename="user")
router.register("profiles", hub_api.UserProfileViewSet, basename="profile")
router.register("projects", hub_api.ProjectViewSet, basename="project")
router.register("tags", hub_api.TagViewSet, basename="tag")
router.register("tasks", hub_api.TaskViewSet, basename="task")
router.register("assignments", hub_api.TaskAssignmentViewSet, basename="assignment")
router.register("threads", hub_api.ThreadViewSet, basename="thread")
router.register("messages", hub_api.MessageViewSet, basename="message")
router.register("audit-events", hub_api.AuditEventViewSet, basename="audit-event")

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("hub.urls")),
    path("api/", include(router.urls)),
    path("api/auth/token/", obtain_auth_token, name="api-token"),
    path("graphql/", GraphQLView.as_view(schema=schema, graphiql=True)),
]
