import logging
import math

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

AVG_SPEED_MPH = 55.0


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Approximate distance in miles between two (lat, lng) points."""
    R = 3959  # Earth radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _dev_multi_leg_route(waypoints: list[tuple]) -> dict:
    """Dev fallback: Haversine distance when ORS_API_KEY is not set."""
    total_miles = 0.0
    legs = []
    for i in range(len(waypoints) - 1):
        lat1, lng1 = waypoints[i]
        lat2, lng2 = waypoints[i + 1]
        dist = _haversine_miles(lat1, lng1, lat2, lng2)
        total_miles += dist
        legs.append(
            {
                "distance_miles": dist,
                "duration_hours": dist / AVG_SPEED_MPH,
                "steps": [],
            }
        )
    total_hours = total_miles / AVG_SPEED_MPH
    # Simple GeoJSON LineString from waypoints
    coords = [[wp[1], wp[0]] for wp in waypoints]
    geometry = {"type": "LineString", "coordinates": coords}
    return {
        "distance_miles": total_miles,
        "duration_hours": total_hours,
        "geometry": geometry,
        "legs": legs,
    }


def get_route(origin: tuple, destination: tuple) -> dict | None:
    """
    Gets driving route between two (lat, lng) points via OpenRouteService.
    Returns dict with distance_miles, duration_hours, geometry (GeoJSON), steps.
    """
    api_key = settings.ORS_API_KEY
    if not api_key:
        logger.warning("ORS_API_KEY not configured, routing unavailable")
        return None

    url = f"{settings.ORS_BASE_URL}/v2/directions/driving-hgv"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": [
            [origin[1], origin[0]],  # ORS expects [lng, lat]
            [destination[1], destination[0]],
        ],
        "geometry": True,
        "instructions": True,
        "units": "mi",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        route = data["routes"][0]
        summary = route["summary"]

        return {
            "distance_miles": summary["distance"],
            "duration_hours": summary["duration"] / 3600.0,
            "geometry": route.get("geometry"),
            "steps": route.get("segments", [{}])[0].get("steps", []),
        }
    except (requests.RequestException, KeyError, IndexError):
        logger.exception("ORS routing request failed from %s to %s", origin, destination)
        return None


def get_multi_leg_route(waypoints: list[tuple]) -> dict | None:
    """
    Routes through multiple waypoints: [(lat,lng), (lat,lng), ...].
    Returns combined distance, duration, geometry, and per-leg breakdowns.
    """
    if len(waypoints) < 2:
        return None

    api_key = getattr(settings, "ORS_API_KEY", None)
    if not api_key:
        logger.warning("ORS_API_KEY not configured, using dev fallback (Haversine)")
        return _dev_multi_leg_route(waypoints)

    url = f"{settings.ORS_BASE_URL}/v2/directions/driving-hgv"
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }
    coords = [[wp[1], wp[0]] for wp in waypoints]
    body = {
        "coordinates": coords,
        "geometry": True,
        "instructions": True,
        "units": "mi",
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        route = data["routes"][0]
        summary = route["summary"]
        segments = route.get("segments", [])

        legs = []
        for seg in segments:
            legs.append(
                {
                    "distance_miles": seg["distance"],
                    "duration_hours": seg["duration"] / 3600.0,
                    "steps": seg.get("steps", []),
                }
            )

        return {
            "distance_miles": summary["distance"],
            "duration_hours": summary["duration"] / 3600.0,
            "geometry": route.get("geometry"),
            "legs": legs,
        }
    except (requests.RequestException, KeyError, IndexError):
        logger.warning("ORS multi-leg routing failed, using dev fallback (Haversine)")
        return _dev_multi_leg_route(waypoints)
