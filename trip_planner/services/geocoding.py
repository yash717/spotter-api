import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from trip_planner.models import GeocodeCache

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 30


def geocode_address(raw_input: str) -> dict | None:
    """
    Resolves an address string to lat/lng.
    Checks GeocodeCache first, then calls OpenRouteService.
    Returns dict with lat, lng, canonical_address or None on failure.
    """
    raw_input = raw_input.strip()
    if not raw_input:
        return None

    cached = GeocodeCache.objects.filter(
        raw_input__iexact=raw_input,
        expires_at__gt=timezone.now(),
    ).first()

    if cached:
        return {
            "lat": float(cached.resolved_lat),
            "lng": float(cached.resolved_lng),
            "canonical_address": cached.canonical_address,
        }

    result = _call_ors_geocode(raw_input)
    if result is None:
        return None

    GeocodeCache.objects.create(
        raw_input=raw_input,
        resolved_lat=result["lat"],
        resolved_lng=result["lng"],
        canonical_address=result["canonical_address"],
        provider="openrouteservice",
        confidence_score=result.get("confidence", 0.0),
        expires_at=timezone.now() + timedelta(days=CACHE_TTL_DAYS),
    )

    return result


def _call_ors_geocode(address: str) -> dict | None:
    api_key = settings.ORS_API_KEY
    if not api_key:
        logger.warning("ORS_API_KEY not configured, geocoding unavailable")
        return None

    url = f"{settings.ORS_BASE_URL}/geocode/search"
    params = {
        "api_key": api_key,
        "text": address,
        "size": 1,
        "boundary.country": "US",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            logger.warning("No geocode results for: %s", address)
            return None

        coords = features[0]["geometry"]["coordinates"]
        props = features[0].get("properties", {})
        return {
            "lng": coords[0],
            "lat": coords[1],
            "canonical_address": props.get("label", address),
            "confidence": props.get("confidence", 0.0),
        }
    except requests.RequestException:
        logger.exception("ORS geocode request failed for: %s", address)
        return None
