"""Live geocoding and air quality data retrieval via Open-Meteo."""

from dataclasses import dataclass
from typing import Any
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT = 10


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
    hourly_times: list[str]
    hourly_pm2_5: list[float]


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


def find_cleanest_two_hour_window(times: list[str], pm25_values: list[float]) -> str:
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


def fetch_air_quality(city: str) -> AirQualitySnapshot:
    """Geocode a city and fetch live + 24h air quality data."""
    geo_resp = requests.get(
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

    aq_resp = requests.get(
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

    us_aqi = float(current.get("us_aqi") or 0.0)
    pm2_5 = float(current.get("pm2_5") or 0.0)
    pm10 = float(current.get("pm10") or 0.0)
    no2 = float(current.get("nitrogen_dioxide") or 0.0)
    co = float(current.get("carbon_monoxide") or 0.0)
    o3 = float(current.get("ozone") or 0.0)

    times: list[str] = hourly.get("time", [])[:24]
    hourly_pm25: list[float] = [float(v or 0.0) for v in hourly.get("pm2_5", [])[:24]]

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
