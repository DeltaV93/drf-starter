from django.urls import path

from .views import ConnectableServerListView, ConnectedServerDetailView

urlpatterns = [
    path('mcp/servers/', ConnectableServerListView.as_view(), name='mcp_server_list'),
    path(
        'mcp/servers/<slug:slug>/',
        ConnectedServerDetailView.as_view(),
        name='mcp_server_detail',
    ),
]
