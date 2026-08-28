from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from utils.api_utils import api_response
from .models import Trip
from .serializers import TripSerializer, CreateTripSerializer, UpdateTripSerializer


class TripsListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='List user trips',
        responses=TripSerializer(many=True),
    )
    def get(self, request):
        trips = Trip.objects.filter(user=request.user).prefetch_related('homes')
        return api_response(data=TripSerializer(trips, many=True).data)

    @extend_schema(
        summary='Create trip',
        request=CreateTripSerializer,
        responses={201: TripSerializer},
    )
    def post(self, request):
        serializer = CreateTripSerializer(data=request.data, context={'user': request.user})
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        trip = serializer.save()
        return api_response(data=TripSerializer(trip).data, status_code=status.HTTP_201_CREATED)


class TripDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get trip details',
        responses=TripSerializer,
    )
    def get(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, user=request.user)
        return api_response(data=TripSerializer(trip).data)

    @extend_schema(
        summary='Update trip',
        request=UpdateTripSerializer,
        responses=TripSerializer,
    )
    def put(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, user=request.user)
        serializer = UpdateTripSerializer(trip, data=request.data)
        if not serializer.is_valid():
            return api_response(
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        trip = serializer.save()
        return api_response(data=TripSerializer(trip).data)

    @extend_schema(
        summary='Delete trip',
        responses={204: None},
    )
    def delete(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, user=request.user)
        trip.delete()
        return api_response(message='Trip deleted', status_code=status.HTTP_204_NO_CONTENT)


class GeocodeView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary='Geocode address',
        request={'type': 'object', 'properties': {'address': {'type': 'string'}}},
        responses={'type': 'object'},
    )
    def post(self, request):
        from .utils.geocoding import geocode_address

        address = request.data.get('address')
        if not address:
            return api_response(
                errors={'address': ['Address is required']},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat, lng = geocode_address(address)
            return api_response(data={'lat': float(lat), 'lng': float(lng)})
        except Exception as e:
            return api_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )


class OptimizeRouteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    @extend_schema(
        summary='Optimize route',
        request={'type': 'object'},
        responses={'type': 'object'},
    )
    def post(self, request):
        from .utils.optimizer import optimize_route

        homes = request.data.get('homes', [])
        if not homes:
            return api_response(
                errors={'homes': ['Homes list is required']},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            optimized = optimize_route(homes)
            return api_response(data=optimized)
        except Exception as e:
            return api_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
