import redis
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse


def healthz(request):
    """Lightweight liveness/readiness probe for load balancers and uptime monitors.

    Checks the default database connection and the Celery broker (Redis).
    Returns 200 with per-check status when healthy, 503 otherwise.
    """

    checks = {}
    healthy = True

    try:
        connections["default"].cursor().execute("SELECT 1")
        checks["database"] = "ok"
    except OperationalError as error:
        checks["database"] = f"error: {error}"
        healthy = False

    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2)
        client.ping()
        checks["redis"] = "ok"
    except redis.RedisError as error:
        checks["redis"] = f"error: {error}"
        healthy = False

    return JsonResponse({"status": "ok" if healthy else "error", "checks": checks}, status=200 if healthy else 503)
