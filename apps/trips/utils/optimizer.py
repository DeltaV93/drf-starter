from datetime import datetime, timedelta
from geopy.distance import geodesic
from .geocoding import geocode_address_cached


def optimize_route(
    homes,
    start_address=None,
    end_address=None,
    visit_duration_minutes=10,
    avg_speed_mph=30.0
):
    """
    Optimize the route to visit open houses.

    Args:
        homes: List of dicts with keys: address, start_time, end_time
        start_address: Starting location address
        end_address: Ending location address
        visit_duration_minutes: How long to spend at each house
        avg_speed_mph: Average travel speed

    Returns:
        Dict with:
        - schedule: List of optimized visits
        - start_coords: Starting location coordinates
        - end_coords: Ending location coordinates
        - total_distance: Total miles traveled
        - skipped_homes: List of addresses that couldn't be visited
    """
    visit_duration = timedelta(minutes=visit_duration_minutes)

    # Use first home as start/end if not provided
    if not start_address and homes:
        start_address = homes[0]['address']
    if not end_address and homes:
        end_address = homes[0]['address']

    # Geocode start and end locations
    try:
        start_coords = geocode_address_cached(start_address)
    except ValueError:
        raise ValueError(f'Could not geocode start location: {start_address}')

    try:
        end_coords = geocode_address_cached(end_address)
    except ValueError:
        raise ValueError(f'Could not geocode end location: {end_address}')

    # Process homes: geocode and parse times
    processed_homes = []
    skipped = []

    for home in homes:
        try:
            coords = geocode_address_cached(home['address'])
        except ValueError:
            skipped.append(home['address'])
            continue

        try:
            start_dt = datetime.fromisoformat(home['start_time'])
            end_dt = datetime.fromisoformat(home['end_time'])
        except (ValueError, KeyError):
            skipped.append(f"{home['address']} (invalid time format)")
            continue

        processed_homes.append({
            'address': home['address'],
            'coordinates': coords,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'distance_from_start': geodesic(start_coords, coords).miles,
        })

    if not processed_homes:
        return {
            'schedule': [],
            'start_coords': start_coords,
            'end_coords': end_coords,
            'total_distance': 0.0,
            'skipped_homes': skipped,
        }

    # Sort by distance from start, then by start time
    processed_homes.sort(key=lambda h: (h['distance_from_start'], h['start_dt']))

    # Build schedule
    schedule = []
    current_time = min(h['start_dt'] for h in processed_homes)
    current_location = start_coords
    total_distance = 0.0
    order = 1

    for home in processed_homes:
        travel_distance = geodesic(current_location, home['coordinates']).miles
        travel_time = timedelta(hours=travel_distance / avg_speed_mph)
        arrival_time = max(current_time + travel_time, home['start_dt'])

        if arrival_time <= home['end_dt']:
            leave_time = arrival_time + visit_duration

            schedule.append({
                'address': home['address'],
                'arrival_time': arrival_time.isoformat(),
                'leave_time': leave_time.isoformat(),
                'open_house_start': home['start_dt'].isoformat(),
                'open_house_end': home['end_dt'].isoformat(),
                'distance_from_previous': round(travel_distance, 2),
                'lat': float(home['coordinates'][0]),
                'lng': float(home['coordinates'][1]),
                'order': order,
            })

            total_distance += travel_distance
            current_time = leave_time
            current_location = home['coordinates']
            order += 1
        else:
            skipped.append(f"{home['address']} (can't arrive before close)")

    # Add distance to end location
    if schedule:
        final_distance = geodesic(current_location, end_coords).miles
        total_distance += final_distance

    return {
        'schedule': schedule,
        'start_coords': start_coords,
        'end_coords': end_coords,
        'total_distance': round(total_distance, 2),
        'skipped_homes': skipped,
    }
