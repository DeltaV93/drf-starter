"""Answer platform health probes before host and scheme validation.

Platform health checks are the one request that cannot be allowed to fail for
environmental reasons, and by default two things make them fail:

- they arrive over plain HTTP inside the network, so SECURE_SSL_REDIRECT
  turns them into a 301 rather than the 200 the probe wants
- they carry the platform's own Host header (Railway uses
  healthcheck.railway.app), which is not in ALLOWED_HOSTS, so Django answers
  400 DisallowedHost

Both were live bugs on the first Railway deploy. This middleware sits first
in MIDDLEWARE and short-circuits the probe paths before SecurityMiddleware
runs and before anything calls request.get_host().

Bypassing ALLOWED_HOSTS here is safe precisely because these responses are
static: they never reflect the Host header or build a URL from it, which is
what ALLOWED_HOSTS exists to protect against.
"""

from django.http import JsonResponse

from .health import LIVENESS_PATH, READINESS_PATH, check_database


def _envelope(data, message, ok=True):
    """Match utils.api_utils.api_response, so probes and views agree."""
    return JsonResponse(
        {'status': 'success' if ok else 'error', 'message': message, 'data': data},
        status=200 if ok else 503,
    )


class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # request.path is populated from the raw path and needs no host.
        if request.path == LIVENESS_PATH:
            return _envelope({'status': 'ok'}, 'Service is running.')

        if request.path == READINESS_PATH:
            healthy = check_database()
            return _envelope(
                {'checks': {'database': healthy}},
                'Ready.' if healthy else 'One or more dependencies are unavailable.',
                ok=healthy,
            )

        return self.get_response(request)
