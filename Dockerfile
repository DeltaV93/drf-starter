# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder: compile wheels for every dependency.
#
# Kept separate so the runtime image carries no compilers and no build headers.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements are copied on their own so the wheel build is cached until a
# dependency actually changes, not on every source edit.
COPY requirements/ /app/requirements/
COPY requirements.txt /app/

ARG REQUIREMENTS=requirements/prod.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r ${REQUIREMENTS}


# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=template.settings

# libpq is needed at runtime; the -dev headers and compilers are not.
RUN apt-get update && apt-get install --no-install-recommends -y \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user.
RUN groupadd --system app && useradd --system --gid app --create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app . /app

RUN chmod +x /app/entrypoint.sh

# Static files are collected at build time -- it needs no database, only
# settings that import cleanly. Migrations are NOT run here: they need a live
# database, which does not exist during a build. entrypoint.sh runs them.
RUN SECRET_KEY=build-only-not-used-at-runtime \
    DJANGO_ENVIRONMENT=production \
    ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

USER app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "template.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
