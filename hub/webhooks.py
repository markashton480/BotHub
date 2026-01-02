import hmac
import json
import logging
import time
from hashlib import sha256
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

from .models import Webhook

logger = logging.getLogger(__name__)


def build_event_payload(audit_event):
    actor = None
    if audit_event.actor:
        actor = {
            "id": audit_event.actor_id,
            "username": audit_event.actor.get_username(),
            "email": audit_event.actor.email,
        }
    target = None
    if audit_event.target_content_type:
        target = {
            "app_label": audit_event.target_content_type.app_label,
            "model": audit_event.target_content_type.model,
            "id": audit_event.target_object_id,
        }
    return {
        "id": audit_event.id,
        "event": audit_event.verb,
        "actor": actor,
        "target": target,
        "metadata": audit_event.metadata or {},
        "created_at": audit_event.created_at.isoformat(),
    }


def sign_payload(secret, body):
    return hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()


def deliver_webhook(webhook, payload):
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if webhook.secret:
        headers["X-BotHub-Signature"] = sign_payload(webhook.secret, body)
    request = Request(webhook.url, data=body, headers=headers, method="POST")
    timeout = getattr(settings, "WEBHOOK_TIMEOUT_SECONDS", 5)
    started = time.time()
    try:
        with urlopen(request, timeout=timeout) as response:
            response.read()
    except URLError as exc:
        logger.warning("Webhook delivery failed: %s", exc)
    finally:
        elapsed = time.time() - started
        logger.debug("Webhook delivered in %.2fs to %s", elapsed, webhook.url)


def dispatch_webhooks(audit_event):
    payload = build_event_payload(audit_event)
    for webhook in Webhook.objects.filter(is_active=True):
        events = webhook.events or []
        if events and audit_event.verb not in events:
            continue
        deliver_webhook(webhook, payload)
