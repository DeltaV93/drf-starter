import re
import time
import threading
from functools import lru_cache
from geopy.geocoders import Nominatim

# Rate limiting: Nominatim requires max 1 request per second
# Using a lock for thread-safety
_rate_limit_lock = threading.Lock()
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 1.1  # seconds

geolocator = Nominatim(user_agent='clearpath-open-house-scheduler')


def clean_address(address: str) -> str:
    """Clean address for better geocoding results."""
    # Remove ZIP+4 if present
    address = re.sub(r'(\d{5})-\d{4}', r'\1', address)
    # Remove trailing USA
    address = re.sub(r'\s*,?\s*USA$', '', address.strip(), flags=re.IGNORECASE)
    # Remove duplicate street names
    words = address.split()
    cleaned_words = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() != words[i - 1].lower():
            cleaned_words.append(word)
    return ' '.join(cleaned_words)


def _rate_limit():
    """Ensure we don't exceed Nominatim's rate limit (thread-safe)."""
    global _last_request_time
    with _rate_limit_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()


def geocode_address(address: str, retries: int = 3) -> tuple[float, float]:
    """Get coordinates for an address with rate limiting and retries."""
    cleaned = clean_address(address)

    for attempt in range(retries):
        try:
            _rate_limit()
            location = geolocator.geocode(cleaned)
            if location:
                return (location.latitude, location.longitude)
        except Exception as e:
            time.sleep(1)

    raise ValueError(f'Could not geocode address: {address}')


@lru_cache(maxsize=100)
def geocode_address_cached(address: str) -> tuple[float, float]:
    """Cached version of geocode_address for repeated lookups."""
    return geocode_address(address)
