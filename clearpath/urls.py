from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

# Everything the SPA talks to lives under a version prefix so a breaking
# change can ship as /api/v2/ alongside the old routes.
api_v1_patterns = [
    path('', include('apps.core.urls')),
    path('', include('apps.authentication.urls')),
    path('', include('apps.users.urls')),
]

if settings.STRIPE_ENABLED:
    api_v1_patterns.append(path('', include('apps.subscriptions.urls')))

if settings.ORGANIZATIONS_ENABLED:
    api_v1_patterns.append(path('', include('apps.organizations.urls')))

if settings.API_KEYS_ENABLED:
    api_v1_patterns.append(path('', include('apps.api_keys.urls')))

if settings.AUDIT_LOG_ENABLED:
    api_v1_patterns.append(path('', include('apps.audit.urls')))

if settings.UPLOADS_ENABLED:
    api_v1_patterns.append(path('', include('apps.uploads.urls')))

if settings.MCP_CLIENT_ENABLED:
    api_v1_patterns.append(path('', include('apps.mcp_client.urls')))

if settings.TRIPS_ENABLED:
    api_v1_patterns.append(path('', include('apps.trips.urls')))

if settings.DOCUMENTS_ENABLED:
    api_v1_patterns.append(path('', include('apps.documents.urls')))

if settings.SHARES_ENABLED:
    api_v1_patterns.append(path('', include('apps.shares.urls')))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include((api_v1_patterns, 'v1'), namespace='v1')),
    # Schema and documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/docs/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.MCP_OAUTH_ENABLED:
    # At the root, not under the version prefix: a well-known URI is fixed by
    # RFC 9728 and cannot carry one.
    urlpatterns.append(path('', include('apps.mcp_oauth.urls')))

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar  # noqa: F401
    except ImportError:
        pass
    else:
        urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))

# The SPA catch-all must stay LAST, and it has to reject two kinds of path or
# it hands back index.html for things that are not client-side routes.
#
# Prefixes Django or WhiteNoise owns. `admin` is matched with and without the
# trailing slash: excluding only `admin/` meant `/admin` fell through to the
# catch-all, which *resolved* it -- and because it resolved, CommonMiddleware's
# APPEND_SLASH never redirected. `/admin` returned the SPA instead of the login
# page. `assets/` is where Vite writes its hashed bundles.
#
# `.well-known/` is excluded unconditionally, not under MCP_OAUTH_ENABLED. A
# discovery client that probes for the metadata document with the flag off
# must get a 404 -- the SPA's index.html with a 200 tells it the document
# exists and then fails to parse as JSON, which is a much worse answer than
# "there is nothing here".
SPA_EXCLUDED_PREFIXES = r'api/|admin(?:/|$)|assets/|static/|media/|__debug__/|\.well-known/'

# Anything with a file extension. A client-side route has none, so a dotted
# final segment is an asset that WhiteNoise did not serve -- meaning it is
# missing. Returning index.html for it gives the browser HTML where it asked
# for JavaScript, and a page that fails silently as a blank screen. A 404 says
# what actually happened.
#
# The optional trailing slash matters: without it `/favicon.ico` 404s, then
# APPEND_SLASH retries `/favicon.ico/`, which no longer looks like a file and
# so gets the SPA -- the same bug one redirect further along.
SPA_FILE_LIKE_PATH = r'.*\.[^/]*/?$'

if settings.SERVE_SPA:
    from apps.core.views import SPAView

    urlpatterns.append(
        re_path(
            rf'^(?!{SPA_EXCLUDED_PREFIXES})(?!{SPA_FILE_LIKE_PATH}).*$',
            SPAView.as_view(),
            name='spa',
        )
    )
