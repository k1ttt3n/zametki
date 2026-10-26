import time

from django.conf import settings

# Простое in-memory окно: IP -> список таймстемпов попыток входа.
_attempts = {}


def client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_limited(ip):
    now = time.time()
    hits = [t for t in _attempts.get(ip, []) if now - t < 60]
    _attempts[ip] = hits
    return len(hits) >= getattr(settings, "LOGIN_RATE_LIMIT", 10)


def register_attempt(ip):
    _attempts.setdefault(ip, []).append(time.time())


class LoginThrottleMiddleware:
    """Не более LOGIN_RATE_LIMIT попыток входа в минуту с одного IP."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/api/auth/login" and request.method == "POST":
            ip = client_ip(request)
            if is_limited(ip):
                from django.http import JsonResponse
                return JsonResponse(
                    {"errors": {"detail": "Слишком много попыток входа. Повторите через минуту."}},
                    status=429,
                )
            response = self.get_response(request)
            if response.status_code in (400, 401):
                register_attempt(ip)
            else:
                _attempts.pop(ip, None)
            return response
        return self.get_response(request)
