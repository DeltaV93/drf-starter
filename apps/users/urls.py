from django.urls import path

from .views import MeView

urlpatterns = [
    path('users/me/', MeView.as_view(), name='user_me'),
]
