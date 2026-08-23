"""Logging helpers.

Handler and formatter configuration lives in settings.LOGGING -- this module
deliberately does not call logging.basicConfig(), which would fight it.
"""

import logging
import time
from functools import wraps

SENSITIVE_FIELDS = frozenset(
    {
        'password',
        'password2',
        'password_confirm',
        'token',
        'api_key',
        'secret',
        'authorization',
        'csrfmiddlewaretoken',
    }
)

REDACTED = '****'


def get_logger(name):
    """Get a logger for a module. Pass __name__."""
    return logging.getLogger(name)


def log_exception(logger):
    """Log and re-raise any exception escaping the decorated function."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception:
                logger.exception('Exception in %s', func.__name__)
                raise

        return wrapper

    return decorator


def timed_function(logger, level=logging.DEBUG):
    """Log how long the decorated function took, including on failure."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                logger.log(level, '%s took %.3fs', func.__name__, elapsed)

        return wrapper

    return decorator


def sanitize_log_data(data):
    """Redact sensitive keys before logging a dict. Recurses into nested dicts."""
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if str(key).lower() in SENSITIVE_FIELDS:
            sanitized[key] = REDACTED
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    return sanitized


class RequestLogger:
    """Log request/response pairs for a view."""

    def __init__(self, logger):
        self.logger = logger

    def log_request(self, request):
        self.logger.info('%s %s', request.method, request.path)

    def log_response(self, response, request):
        self.logger.info('%s %s -> %s', request.method, request.path, response.status_code)
