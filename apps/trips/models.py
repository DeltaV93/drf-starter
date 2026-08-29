from django.db import models
from django.conf import settings


class Trip(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    name = models.CharField(max_length=255)
    start_address = models.CharField(max_length=500)
    end_address = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.user.email})'


class TripHome(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='homes')
    address = models.CharField(max_length=500)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    visit_order = models.IntegerField()
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)

    # Zillow data
    zpid = models.CharField(max_length=20, null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.FloatField(null=True, blank=True)
    sqft = models.IntegerField(null=True, blank=True)
    photos = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['trip', 'visit_order']),
        ]
        ordering = ['visit_order']

    def __str__(self):
        return f'{self.address} ({self.trip.name})'
