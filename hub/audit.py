from django.contrib.contenttypes.models import ContentType

from .models import AuditEvent
from .webhooks import dispatch_webhooks


def log_event(actor, verb, target=None, metadata=None):
    content_type = None
    object_id = None
    if target is not None:
        content_type = ContentType.objects.get_for_model(target)
        object_id = target.pk
    audit_event = AuditEvent.objects.create(
        actor=actor,
        verb=verb,
        target_content_type=content_type,
        target_object_id=object_id,
        metadata=metadata or {},
    )
    dispatch_webhooks(audit_event)
