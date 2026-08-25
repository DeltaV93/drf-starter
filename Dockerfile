# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Frontend: build the SPA.
#
# The output is served by Django in the runtime image, which keeps the SPA and
# the API on one origin -- what the session-cookie and CSRF design assumes.
# VITE_API_BASE_URL is therefore a relative path: the app calls its own origin.
# ---------------------------------------------------------------------------
FROM node:26-slim AS frontend

WORKDIR /app/website

# package files first so npm ci is cached until dependencies actually change.
COPY website/package.json website/package-lock.json ./
RUN npm ci

COPY website/ ./

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_STRIPE_ENABLED=false
ARG VITE_ORGANIZATIONS_ENABLED=false
ARG VITE_SOCIAL_AUTH_ENABLED=false
ARG VITE_TWO_FACTOR_ENABLED=false
ARG VITE_API_KEYS_ENABLED=false
ARG VITE_UPLOADS_ENABLED=false
ARG VITE_AUDIT_LOG_ENABLED=false
ARG VITE_STRIPE_PUBLISHABLE_KEY=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_STRIPE_ENABLED=${VITE_STRIPE_ENABLED} \
    VITE_ORGANIZATIONS_ENABLED=${VITE_ORGANIZATIONS_ENABLED} \
    VITE_SOCIAL_AUTH_ENABLED=${VITE_SOCIAL_AUTH_ENABLED} \
    VITE_TWO_FACTOR_ENABLED=${VITE_TWO_FACTOR_ENABLED} \
    VITE_API_KEYS_ENABLED=${VITE_API_KEYS_ENABLED} \
    VITE_UPLOADS_ENABLED=${VITE_UPLOADS_ENABLED} \
    VITE_AUDIT_LOG_ENABLED=${VITE_AUDIT_LOG_ENABLED} \
    VITE_STRIPE_PUBLISHABLE_KEY=${VITE_STRIPE_PUBLISHABLE_KEY}

RUN npm run build


# ---------------------------------------------------------------------------
# Builder: compile wheels for every dependency.
#
# Kept separate so the runtime image carries no compilers and no build headers.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS builder

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
FROM python:3.14-slim AS runtime

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

# The built SPA. Django serves it from here; see SPA_DIST_DIR in settings.
COPY --from=frontend --chown=app:app /app/website/dist /app/website/dist

RUN chmod +x /app/entrypoint.sh

# Static files are collected at build time -- it needs no database, only
# settings that import cleanly. Migrations are NOT run here: they need a live
# database, which does not exist during a build. entrypoint.sh runs them.
# DATABASE_URL is parsed but never connected to -- production settings refuse
# to fall back to a localhost database, and collectstatic still needs them to
# import cleanly.
RUN SECRET_KEY=build-only-not-used-at-runtime \
    DJANGO_ENVIRONMENT=production \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://build:build@db.invalid:5432/build \
    FRONTEND_URL=https://build.invalid \
    python manage.py collectstatic --noinput

USER app

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

# Shell form so ${PORT} expands: managed hosts assign the port and route to it.
CMD ["sh", "-c", "gunicorn template.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --access-logfile - --error-logfile -"]
