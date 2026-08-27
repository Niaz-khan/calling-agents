from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def root(request):
    return JsonResponse(
        {"message": "AI Calling Agent", "version": settings.APP_VERSION}
    )


def health(request):
    return JsonResponse({"status": "ok"})


def db_health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})