from datetime import datetime, timedelta, timezone

import requests


NWS_BASE = "https://api.weather.gov"
COOPS_BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
USER_AGENT = "Naftelia/1.0 (contact: tanveersinghjandu.dev@gmail.com)"


def _headers():
    return {"User-Agent": USER_AGENT, "Accept": "application/geo+json, application/json"}


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_json(url, params=None, timeout=12):
    response = requests.get(url, params=params, headers=_headers(), timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_nws_forecast(lat, lon):
    """NOAA/NWS point forecast. Coverage is mainly U.S. and territories."""
    point = _get_json(f"{NWS_BASE}/points/{lat},{lon}")
    properties = point.get("properties", {})
    forecast_hourly_url = properties.get("forecastHourly")
    forecast_url = properties.get("forecast")
    alerts_url = f"{NWS_BASE}/alerts/active"

    hourly = []
    daily = []
    alerts = []

    if forecast_hourly_url:
        hourly_data = _get_json(forecast_hourly_url)
        hourly = hourly_data.get("properties", {}).get("periods", [])[:24]

    if forecast_url:
        daily_data = _get_json(forecast_url)
        daily = daily_data.get("properties", {}).get("periods", [])[:6]

    try:
        alert_data = _get_json(alerts_url, {"point": f"{lat},{lon}"})
        alerts = [
            {
                "event": item.get("properties", {}).get("event"),
                "severity": item.get("properties", {}).get("severity"),
                "headline": item.get("properties", {}).get("headline"),
            }
            for item in alert_data.get("features", [])
        ]
    except requests.RequestException:
        alerts = []

    return {
        "provider": "NOAA National Weather Service",
        "office": properties.get("cwa"),
        "grid": {"x": properties.get("gridX"), "y": properties.get("gridY")},
        "hourly": hourly,
        "daily": daily,
        "alerts": alerts,
    }


def coops_latest(station_id, product):
    params = {
        "product": product,
        "application": "Naftelia",
        "date": "latest",
        "station": station_id,
        "time_zone": "gmt",
        "units": "metric",
        "format": "json",
    }
    data = _get_json(COOPS_BASE, params=params)
    observations = data.get("data", [])
    if not observations:
        return None
    return observations[-1]


def coops_predictions(station_id, hours=24):
    now = datetime.now(timezone.utc)
    end = now + timedelta(hours=hours)
    params = {
        "product": "predictions",
        "application": "Naftelia",
        "begin_date": now.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
        "station": station_id,
        "datum": "MLLW",
        "time_zone": "gmt",
        "units": "metric",
        "interval": "h",
        "format": "json",
    }
    data = _get_json(COOPS_BASE, params=params)
    return data.get("predictions", [])[: hours + 1]


def get_coops_station_conditions(station_id):
    if not station_id:
        return {"provider": "NOAA CO-OPS", "station_id": None, "available": False, "observations": {}}

    products = ["wind", "water_temperature", "air_temperature", "air_pressure", "visibility"]
    observations = {}
    errors = {}
    for product in products:
        try:
            observations[product] = coops_latest(station_id, product)
        except requests.RequestException as exc:
            errors[product] = exc.__class__.__name__

    try:
        predictions = coops_predictions(station_id)
    except requests.RequestException:
        predictions = []

    return {
        "provider": "NOAA CO-OPS",
        "station_id": station_id,
        "available": bool(observations),
        "observations": observations,
        "predictions": predictions,
        "errors": errors,
    }


def summarize_noaa_conditions(origin, destination, station_id=None):
    origin_lat = origin["lat"]
    origin_lon = origin["lon"]
    destination_lat = destination["lat"]
    destination_lon = destination["lon"]

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "origin": origin,
        "destination": destination,
        "nws": {"origin": None, "destination": None, "errors": {}},
        "coops": get_coops_station_conditions(station_id),
    }

    for label, lat, lon in (
        ("origin", origin_lat, origin_lon),
        ("destination", destination_lat, destination_lon),
    ):
        try:
            result["nws"][label] = get_nws_forecast(lat, lon)
        except requests.RequestException as exc:
            result["nws"]["errors"][label] = {
                "type": exc.__class__.__name__,
                "message": "NOAA/NWS forecast unavailable for this point. This can happen outside U.S. coverage.",
            }

    return result


def extract_risk_signals(noaa_snapshot):
    hourly = []
    for point in ("origin", "destination"):
        hourly.extend((noaa_snapshot.get("nws", {}).get(point) or {}).get("hourly") or [])

    wind_speeds = []
    for item in hourly:
        speed = item.get("windSpeed", "")
        number = "".join(ch for ch in speed if ch.isdigit() or ch == " ")
        first = number.split()[0] if number.split() else None
        parsed = _safe_float(first)
        if parsed is not None:
            wind_speeds.append(parsed)

    coops = noaa_snapshot.get("coops", {}).get("observations", {})
    wind_obs = coops.get("wind") or {}
    water_temp = coops.get("water_temperature") or {}
    visibility = coops.get("visibility") or {}

    return {
        "max_forecast_wind_mph": max(wind_speeds) if wind_speeds else None,
        "station_wind_speed": wind_obs.get("s"),
        "station_wind_direction": wind_obs.get("d"),
        "water_temperature_c": water_temp.get("v"),
        "visibility": visibility.get("v"),
        "active_alerts": [
            alert
            for point in ("origin", "destination")
            for alert in ((noaa_snapshot.get("nws", {}).get(point) or {}).get("alerts") or [])
        ],
    }
