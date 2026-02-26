import logging
import re
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from trip_planner.models import GeocodeCache

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 30

# Dev fallback: known US cities when ORS_API_KEY is not set
DEV_CITY_COORDS = {
    "chicago": (41.8781, -87.6298),
    "dallas": (32.7767, -96.7970),
    "memphis": (35.1495, -90.0490),
    "atlanta": (33.7490, -84.3880),
    "houston": (29.7604, -95.3698),
    "los angeles": (34.0522, -118.2437),
    "denver": (39.7392, -104.9903),
    "nashville": (36.1627, -86.7816),
    "phoenix": (33.4484, -112.0740),
    "indianapolis": (39.7684, -86.1581),
    "new york": (40.7128, -74.0060),
    "miami": (25.7617, -80.1918),
    "seattle": (47.6062, -122.3321),
    "boston": (42.3601, -71.0589),
    "detroit": (42.3314, -83.0458),
    "philadelphia": (39.9526, -75.1652),
    "san francisco": (37.7749, -122.4194),
}


def _extract_city_from_address(address: str) -> str | None:
    """Extract city name from full US address (e.g. '123 Main St, Chicago, IL')."""
    addr = address.strip()
    if not addr:
        return None
    # Try "Address, City, ST" or "Address, City, State" pattern
    match = re.search(r",\s*([^,]+?)\s*,\s*(?:[A-Z]{2}|[A-Za-z]+)(?:\s+\d{5})?$", addr)
    if match:
        return match.group(1).strip().lower()
    # Fallback: "Address, City" - use second-to-last part as city when 3+ parts
    parts = [p.strip().lower() for p in addr.split(",")]
    if len(parts) >= 2:
        city_candidate = parts[-2] if len(parts) > 2 else parts[-1]
        if city_candidate and city_candidate not in ("us", "usa"):
            return city_candidate
    return addr.lower()


def _dev_geocode(address: str) -> dict | None:
    """Fallback when ORS fails or is not configured. Matches city names."""
    addr_lower = address.strip().lower()
    extracted = _extract_city_from_address(address)
    candidates = [addr_lower]
    if extracted:
        candidates.append(extracted)
    for city, (lat, lng) in DEV_CITY_COORDS.items():
        for cand in candidates:
            if city in cand or re.search(rf"\b{re.escape(city)}\b", cand):
                return {
                    "lat": lat,
                    "lng": lng,
                    "canonical_address": address.strip(),
                    "provider": "dev_fallback",
                }
    return None


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
        result = _dev_geocode(raw_input)
    if result is None:
        return None

    GeocodeCache.objects.create(
        raw_input=raw_input,
        resolved_lat=result["lat"],
        resolved_lng=result["lng"],
        canonical_address=result["canonical_address"],
        provider=result.get("provider", "openrouteservice"),
        confidence_score=result.get("confidence", 0.0),
        expires_at=timezone.now() + timedelta(days=CACHE_TTL_DAYS),
    )

    return result


def geocode_autocomplete(query: str, limit: int = 5) -> list[dict]:
    """
    Returns address suggestions for autocomplete.
    Uses OpenRouteService when configured, else dev fallback with known US cities.
    Each item: { "label": str, "lat": float, "lng": float }
    """
    query = query.strip()
    if not query:
        return []

    result = _call_ors_autocomplete(query, limit)
    if result:
        return result
    return _dev_autocomplete(query, limit)


def _call_ors_autocomplete(query: str, limit: int) -> list[dict]:
    api_key = settings.ORS_API_KEY
    if not api_key:
        return []

    url = f"{settings.ORS_BASE_URL}/geocode/search"
    params = {
        "api_key": api_key,
        "text": query,
        "size": limit,
        "boundary.country": "US",
    }

    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        features = data.get("features", [])
        out = []
        for f in features[:limit]:
            coords = f.get("geometry", {}).get("coordinates", [0, 0])
            props = f.get("properties", {})
            label = props.get("label", query)
            out.append({"label": label, "lat": coords[1], "lng": coords[0]})
        return out
    except requests.RequestException:
        logger.exception("ORS autocomplete failed for: %s", query)
        return []


def _dev_autocomplete(query: str, limit: int) -> list[dict]:
    """Dev fallback: filter known US cities by query. Also matches full addresses containing city."""
    q = query.strip().lower()
    if not q:
        return []
    extracted = _extract_city_from_address(query)
    candidates = [q]
    if extracted:
        candidates.append(extracted)
    out = []
    seen = set()
    for city, (lat, lng) in DEV_CITY_COORDS.items():
        if city in seen:
            continue
        for cand in candidates:
            if city in cand or cand in city or city.startswith(cand) or cand.startswith(city):
                out.append({"label": city.title(), "lat": lat, "lng": lng})
                seen.add(city)
                break
        if len(out) >= limit:
            break
    return out


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
