from django.urls import path
from .views import TripsListView, TripDetailView, GeocodeView, OptimizeRouteView

app_name = 'trips'

urlpatterns = [
    path('trips/', TripsListView.as_view(), name='trips-list'),
    path('trips/<int:pk>/', TripDetailView.as_view(), name='trips-detail'),
    path('geocode/', GeocodeView.as_view(), name='geocode'),
    path('optimize-route/', OptimizeRouteView.as_view(), name='optimize-route'),
]
