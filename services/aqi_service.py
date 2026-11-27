"""Live geocoding and air quality data retrieval via Open-Meteo."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = 10

_HTTP_SESSION = requests.Session()
_HTTP_SESSION.headers.update({"User-Agent": "UrbanAirQualityAssistant/1.0"})


@dataclass(frozen=True)
class AirQualitySnapshot:
    """Structured container for current and 24-hour forecast air quality."""

    city_label: str
    latitude: float
    longitude: float
    us_aqi: float
    pm2_5: float
    pm10: float
    nitrogen_dioxide: float
    carbon_monoxide: float
    ozone: float
    dominant_driver: str
    cleanest_window: str
    hourly_times: tuple[str, ...]
    hourly_pm2_5: tuple[float, ...]


def categorize_us_aqi(us_aqi: float) -> tuple[str, str]:
    """Return the standard US EPA AQI category and plain-language health guidance."""
    if us_aqi <= 50:
        return ("Good", "Air quality is satisfactory with little or no risk.")
    if us_aqi <= 100:
        return (
            "Moderate",
            "Acceptable air quality; sensitive individuals should limit prolonged exertion.",
        )
    if us_aqi <= 150:
        return (
            "Unhealthy for Sensitive Groups",
            "Children, seniors, and people with asthma should reduce prolonged outdoor exertion.",
        )
    if us_aqi <= 200:
        return (
            "Unhealthy",
            "Everyone may begin to experience health effects; limit outdoor activity.",
        )
    if us_aqi <= 300:
        return (
            "Very Unhealthy",
            "Health alert: avoid prolonged outdoor exertion and keep windows sealed.",
        )
    return ("Hazardous", "Emergency conditions: remain indoors with air filtration if possible.")


def classify_pollutant_driver(pm2_5: float, pm10: float, no2: float) -> str:
    """Identify the primary smog driver from pollutant ratios."""
    if no2 >= 60 and pm2_5 >= 35:
        return "Traffic & Combustion Smog (High PM2.5 + NO2)"
    if pm2_5 >= 55:
        return "Severe Fine Particulate / Winter Inversion Haze (High PM2.5)"
    if pm10 > pm2_5 * 2.2 and pm10 >= 80:
        return "Coarse Dust & Construction Particulates (High PM10)"
    if pm2_5 >= 25:
        return "Moderate Urban Particulate Accumulation"
    return "Low-to-Fair Baseline Urban Air"


def find_cleanest_two_hour_window(
    times: Sequence[str], pm25_values: Sequence[float]
) -> str:
    """Find the consecutive 2-hour window with the lowest average PM2.5 in the next 24h."""
    horizon = min(24, len(times), len(pm25_values))
    if horizon < 2:
        return "Insufficient forecast window"

    best_idx = 0
    best_avg = float("inf")
    for i in range(horizon - 1):
        pair_avg = (pm25_values[i] + pm25_values[i + 1]) / 2.0
        if pair_avg < best_avg:
            best_avg = pair_avg
            best_idx = i

    start_hour = times[best_idx].split("T")[-1]
    end_hour = times[best_idx + 1].split("T")[-1]
    return f"{start_hour} – {end_hour} (Avg PM2.5: {best_avg:.1f} µg/m³)"


def fetch_air_quality(
    city: str, session: requests.Session | None = None
) -> AirQualitySnapshot:
    """Geocode a city and fetch live + 24h air quality data."""
    http = session or _HTTP_SESSION

    geo_resp = http.get(
        GEOCODE_URL,
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=REQUEST_TIMEOUT,
    )
    geo_resp.raise_for_status()
    geo_data: dict[str, Any] = geo_resp.json()

    results = geo_data.get("results")
    if not results:
        raise ValueError(f"Could not find coordinates for '{city}'. Try a major nearby city.")

    place = results[0]
    lat = float(place["latitude"])
    lon = float(place["longitude"])
    label_parts = [place.get("name", city), place.get("admin1"), place.get("country")]
    city_label = ", ".join(p for p in label_parts if p)

    aq_resp = http.get(
        AIR_QUALITY_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "us_aqi,pm2_5,pm10,nitrogen_dioxide,carbon_monoxide,ozone",
            "hourly": "pm2_5",
            "forecast_days": 2,
            "timezone": "auto",
        },
        timeout=REQUEST_TIMEOUT,
    )
    aq_resp.raise_for_status()
    aq_data: dict[str, Any] = aq_resp.json()

    current = aq_data.get("current", {})
    hourly = aq_data.get("hourly", {})

    us_aqi = max(0.0, float(current.get("us_aqi") or 0.0))
    pm2_5 = max(0.0, float(current.get("pm2_5") or 0.0))
    pm10 = max(0.0, float(current.get("pm10") or 0.0))
    no2 = max(0.0, float(current.get("nitrogen_dioxide") or 0.0))
    co = max(0.0, float(current.get("carbon_monoxide") or 0.0))
    o3 = max(0.0, float(current.get("ozone") or 0.0))

    raw_times: list[str] = hourly.get("time", [])
    raw_pm25: list[Any] = hourly.get("pm2_5", [])
    current_time = str(current.get("time") or "")
    start_idx = 0
    if current_time:
        hour_prefix = current_time[:13]
        for idx, ts in enumerate(raw_times):
            if str(ts).startswith(hour_prefix):
                start_idx = idx
                break

    times = tuple(raw_times[start_idx : start_idx + 24])
    hourly_pm25 = tuple(
        max(0.0, float(v or 0.0)) for v in raw_pm25[start_idx : start_idx + 24]
    )

    return AirQualitySnapshot(
        city_label=city_label,
        latitude=lat,
        longitude=lon,
        us_aqi=us_aqi,
        pm2_5=pm2_5,
        pm10=pm10,
        nitrogen_dioxide=no2,
        carbon_monoxide=co,
        ozone=o3,
        dominant_driver=classify_pollutant_driver(pm2_5, pm10, no2),
        cleanest_window=find_cleanest_two_hour_window(times, hourly_pm25),
        hourly_times=times,
        hourly_pm2_5=hourly_pm25,
    )
