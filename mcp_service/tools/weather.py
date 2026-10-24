from __future__ import annotations

import requests

from mcp_service.logging_utils import get_logger


logger = get_logger(__name__)


WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    61: "Slight rain", 63: "Rain", 65: "Heavy rain", 71: "Light snow",
    80: "Rain showers", 81: "Rain showers", 95: "Thunderstorm",
}


def get_weather(location: str) -> dict:
    """Use Open-Meteo's public weather and geocoding APIs; no API key is required."""
    try:
        logger.info("Weather request started location_chars=%d", len(location))
        geocode = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        geocode.raise_for_status()
        matches = geocode.json().get("results", [])
        if not matches:
            logger.warning("Weather request failed reason=location_not_found")
            return {"ok": False, "error": f"No location found for '{location}'."}
        match = matches[0]
        forecast = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": match["latitude"], "longitude": match["longitude"],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
            timeout=10,
        )
        forecast.raise_for_status()
        current = forecast.json()["current"]
        result = {
            "ok": True,
            "location": f"{match['name']}, {match.get('country', '')}".rstrip(", "),
            "temperature_c": current["temperature_2m"],
            "condition": WEATHER_CODES.get(current["weather_code"], "Unknown"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
        }
        logger.info("Weather request completed resolved_country=%s", match.get("country", "unknown"))
        return result
    except (KeyError, requests.RequestException, ValueError) as error:
        logger.warning("Weather request failed error_type=%s", type(error).__name__)
        return {"ok": False, "error": f"Weather service failed: {error}"}
