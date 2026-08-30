from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def root(request):
    return JsonResponse(
        {"message": "AI Calling Agent", "version": settings.APP_VERSION}
    )


def _database_healthy() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return True


def health(request):
    return JsonResponse({"status": "ok"})


def db_health(request):
    try:
        _database_healthy()
    except Exception:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


def _redis_healthy() -> bool:
    """Probe Redis through the Django cache backend (redis-backed in prod)."""
    from django.core.cache import cache

    key = "__readiness__"
    cache.set(key, "1", timeout=5)
    if cache.get(key) != "1":
        raise RuntimeError("redis cache probe mismatch")
    cache.delete(key)
    return True


def readiness(request):
    """Readiness probe for production load balancers.

    Verifies the database always, and Redis when REDIS_URL is configured.
    Never leaks connection strings or credentials.
    """
    result = {"status": "ok", "database": "ok", "redis": "not_configured"}
    code = 200

    try:
        _database_healthy()
    except Exception:
        result.update({"status": "error", "database": "error"})
        code = 503

    if settings.REDIS_URL:
        result["redis"] = "ok"
        try:
            _redis_healthy()
        except Exception:
            result.update({"status": "error", "redis": "error"})
            code = 503

    return JsonResponse(result, status=code)