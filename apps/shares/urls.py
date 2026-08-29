from django.urls import path
from .views import ShareLinksListView, ShareLinkDetailView, ShareAccessView

app_name = 'shares'

urlpatterns = [
    path('shares/', ShareLinksListView.as_view(), name='shares-list'),
    path('shares/<int:pk>/', ShareLinkDetailView.as_view(), name='shares-detail'),
    path('share-access/<str:token>/', ShareAccessView.as_view(), name='share-access'),
]
