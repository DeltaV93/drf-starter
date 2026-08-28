from rest_framework import serializers
from .models import Trip, TripHome


class TripHomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripHome
        fields = [
            'id', 'address', 'start_time', 'end_time', 'visit_order',
            'lat', 'lng', 'zpid', 'price', 'bedrooms', 'bathrooms',
            'sqft', 'photos', 'created_at'
        ]


class TripSerializer(serializers.ModelSerializer):
    homes = TripHomeSerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = ['id', 'name', 'start_address', 'end_address', 'homes', 'created_at', 'updated_at']


class CreateTripHomeSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6)
    zpid = serializers.CharField(max_length=20, required=False, allow_blank=True)
    price = serializers.IntegerField(required=False, allow_null=True)
    bedrooms = serializers.IntegerField(required=False, allow_null=True)
    bathrooms = serializers.FloatField(required=False, allow_null=True)
    sqft = serializers.IntegerField(required=False, allow_null=True)
    photos = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class CreateTripSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    start_address = serializers.CharField(max_length=500)
    end_address = serializers.CharField(max_length=500)
    homes = CreateTripHomeSerializer(many=True)

    def create(self, validated_data):
        homes_data = validated_data.pop('homes', [])
        user = self.context['user']
        trip = Trip.objects.create(user=user, **validated_data)

        for idx, home_data in enumerate(homes_data, start=1):
            TripHome.objects.create(trip=trip, visit_order=idx, **home_data)

        return trip


class UpdateTripSerializer(serializers.ModelSerializer):
    homes = CreateTripHomeSerializer(many=True, required=False)

    class Meta:
        model = Trip
        fields = ['name', 'start_address', 'end_address', 'homes']

    def update(self, instance, validated_data):
        homes_data = validated_data.pop('homes', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if homes_data is not None:
            instance.homes.all().delete()
            for idx, home_data in enumerate(homes_data, start=1):
                TripHome.objects.create(trip=instance, visit_order=idx, **home_data)

        return instance


class GeocodeRequestSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500)


class GeocodeResponseSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class OptimizeRouteRequestSerializer(serializers.Serializer):
    homes = CreateTripHomeSerializer(many=True)


class OptimizeRouteResponseSerializer(serializers.Serializer):
    schedule = TripHomeSerializer(many=True)
    start_coords = serializers.ListField(child=serializers.FloatField())
    end_coords = serializers.ListField(child=serializers.FloatField())
    total_distance = serializers.FloatField()
    skipped_homes = serializers.ListField(child=serializers.CharField())
