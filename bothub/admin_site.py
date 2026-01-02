from django.contrib.auth import get_user_model
from unfold.sites import UnfoldAdminSite

from hub.models import AuditEvent, Message, Project, Tag, Task, Thread, Webhook

User = get_user_model()


class BotHubAdminSite(UnfoldAdminSite):
    site_header = "BotHub Admin"
    site_title = "BotHub Admin"
    index_title = "Dashboard"


bot_admin_site = BotHubAdminSite(name="admin")
