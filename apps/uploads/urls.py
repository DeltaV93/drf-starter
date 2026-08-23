from django.urls import path

from .views import AttachmentDetailView, AttachmentDownloadView, AttachmentListCreateView

urlpatterns = [
    path('files/', AttachmentListCreateView.as_view(), name='attachment_list'),
    path(
        'files/<int:attachment_id>/', AttachmentDetailView.as_view(), name='attachment_detail'
    ),
    path(
        'files/<int:attachment_id>/download/',
        AttachmentDownloadView.as_view(),
        name='attachment_download',
    ),
]
