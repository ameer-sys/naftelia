import json
import os
from datetime import datetime, timedelta, timezone

from services.noaa import extract_risk_signals


def _fallback_plan(payload, noaa_snapshot):
    origin = payload["origin"]
    destination = payload["destination"]
    risk = extract_risk_signals(noaa_snapshot)
    max_wind = risk.get("max_forecast_wind_mph") or 0
    caution = "normal"
    if max_wind >= 25 or risk.get("active_alerts"):
        caution = "high"
    elif max_wind >= 15:
        caution = "moderate"

    mid_lat = (origin["lat"] + destination["lat"]) / 2
    mid_lon = (origin["lon"] + destination["lon"]) / 2
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    return {
        "summary": "Use the direct coastal route with conservative speed and continuous weather checks before departure.",
        "safety_level": caution,
        "confidence": 62,
        "expires_at": expires_at,
        "weather_window": "24 hours from generation time",
        "captain_briefing": [
            "Confirm official marine warnings before leaving dock.",
            "Keep enough fuel or battery reserve to return or divert.",
            "Use this route as decision support, not as a replacement for captain judgment.",
        ],
        "waypoints": [
            {
                "label": "Departure",
                "lat": origin["lat"],
                "lon": origin["lon"],
                "instruction": "Depart only after confirming vessel readiness and local conditions.",
                "caution_level": "normal",
            },
            {
                "label": "Mid-route check",
                "lat": mid_lat,
                "lon": mid_lon,
                "instruction": "Reassess wind, visibility, and sea state. Divert early if conditions worsen.",
                "caution_level": caution,
            },
            {
                "label": "Destination approach",
                "lat": destination["lat"],
                "lon": destination["lon"],
                "instruction": "Reduce speed on approach and watch for traffic, shoals, and local restrictions.",
                "caution_level": "normal",
            },
        ],
        "risks": risk,
        "source": "fallback",
    }


def _parse_json(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return json.loads(cleaned)


def build_voyage_plan(payload, noaa_snapshot):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    if not api_key or api_key.startswith("your-"):
        return _fallback_plan(payload, noaa_snapshot)

    prompt = {
        "role": "marine voyage planning assistant",
        "mission": "Create a conservative 24-hour decision-support route for a real vessel operator.",
        "non_negotiables": [
            "Do not guarantee safety.",
            "Tell captains to check official warnings before departure.",
            "Use the NOAA data snapshot as the basis for weather and marine risk.",
            "Return JSON only.",
        ],
        "required_schema": {
            "summary": "short plain-language route recommendation",
            "safety_level": "low | moderate | high",
            "confidence": "integer 0-100",
            "expires_at": "ISO timestamp roughly 24 hours after generation",
            "weather_window": "short text",
            "captain_briefing": ["3-6 short bullet points"],
            "waypoints": [
                {
                    "label": "string",
                    "lat": "number",
                    "lon": "number",
                    "instruction": "plain-language instruction",
                    "caution_level": "normal | moderate | high",
                }
            ],
            "risks": "object with important risk signals",
        },
        "voyage_request": payload,
        "noaa_snapshot": noaa_snapshot,
        "risk_signals": extract_risk_signals(noaa_snapshot),
    }

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=model, contents=json.dumps(prompt))
        plan = _parse_json(response.text)
        plan["source"] = f"Gemini API ({model})"
        return plan
    except Exception as exc:
        plan = _fallback_plan(payload, noaa_snapshot)
        plan["source"] = f"fallback after Gemini error: {exc.__class__.__name__}"
        return plan
