import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


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
            [origin[1], origin[0]],       # ORS expects [lng, lat]
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

    api_key = settings.ORS_API_KEY
    if not api_key:
        return None

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
            legs.append({
                "distance_miles": seg["distance"],
                "duration_hours": seg["duration"] / 3600.0,
                "steps": seg.get("steps", []),
            })

        return {
            "distance_miles": summary["distance"],
            "duration_hours": summary["duration"] / 3600.0,
            "geometry": route.get("geometry"),
            "legs": legs,
        }
    except (requests.RequestException, KeyError, IndexError):
        logger.exception("ORS multi-leg routing failed")
        return None
