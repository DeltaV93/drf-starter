from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
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

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar  # noqa: F401
    except ImportError:
        pass
    else:
        urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))
