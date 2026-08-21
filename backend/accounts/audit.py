import json

from django.core.serializers.json import DjangoJSONEncoder

from .models import AuditEvent


def _json_safe(value):
    return json.loads(json.dumps(value or {}, cls=DjangoJSONEncoder))


def model_snapshot(instance, fields):
    return {field: getattr(instance, field) for field in fields}


def record_audit(request, action, instance=None, *, entity_type=None, entity_id=None, before=None, after=None):
    actor = request.user
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip_address = (forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR")) or None
    return AuditEvent.objects.create(
        workshop=actor.workshop,
        actor=actor,
        action=action,
        entity_type=entity_type or instance._meta.label,
        entity_id=str(entity_id if entity_id is not None else getattr(instance, "pk", "")),
        before=_json_safe(before),
        after=_json_safe(after),
        ip_address=ip_address,
    )
