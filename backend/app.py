import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS

from services.auth0 import require_auth, auth_verifier
from services.db import (
    create_offline_pack,
    create_voyage,
    ensure_user,
    get_voyage,
    init_db,
    list_vessels,
    list_voyages,
    upsert_vessel,
)
from services.gemini import build_voyage_plan
from services.noaa import summarize_noaa_conditions

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

load_dotenv(BASE_DIR / ".env")
load_dotenv(PROJECT_ROOT / ".env")


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    CORS(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})
    init_db()

    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/src/<path:filename>")
    def frontend_src(filename):
        return send_from_directory(FRONTEND_DIR / "src", filename)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "service": "naftelia", "mode": os.getenv("FLASK_ENV", "development")})

    @app.get("/api/config")
    def config():
        return jsonify(
            {
                "demoAuth": True,
                "demoUser": auth_verifier.demo_claims(),
            }
        )

    @app.get("/api/me")
    @require_auth
    def get_profile():
        return jsonify(ensure_user(g.user_claims))

    @app.put("/api/me")
    @require_auth
    def save_profile():
        payload = request.get_json(silent=True) or {}
        return jsonify(ensure_user(g.user_claims, payload))

    @app.get("/api/vessels")
    @require_auth
    def vessels():
        user = ensure_user(g.user_claims)
        return jsonify({"items": list_vessels(user["id"])})

    @app.post("/api/vessels")
    @require_auth
    def save_vessel():
        payload = request.get_json(silent=True) or {}
        if not payload.get("vessel_type"):
            return jsonify({"error": "vessel_type is required"}), 400
        user = ensure_user(g.user_claims)
        return jsonify(upsert_vessel(user["id"], payload)), 201

    @app.post("/api/noaa/conditions")
    def noaa_conditions():
        payload = request.get_json(silent=True) or {}
        missing = _missing(payload, ["origin", "destination"])
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        try:
            snapshot = summarize_noaa_conditions(
                _point(payload["origin"]),
                _point(payload["destination"]),
                station_id=payload.get("station_id"),
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(snapshot)

    @app.post("/api/voyages/plan")
    @require_auth
    def plan_voyage():
        payload = request.get_json(silent=True) or {}
        missing = _missing(payload, ["origin", "destination"])
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        try:
            payload["origin"] = _point(payload["origin"])
            payload["destination"] = _point(payload["destination"])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        user = ensure_user(g.user_claims)
        noaa_snapshot = summarize_noaa_conditions(
            payload["origin"],
            payload["destination"],
            station_id=payload.get("station_id"),
        )
        gemini_plan = build_voyage_plan(payload, noaa_snapshot)
        voyage = create_voyage(user["id"], payload, noaa_snapshot, gemini_plan)
        return jsonify(voyage), 201

    @app.get("/api/voyages")
    @require_auth
    def voyages():
        user = ensure_user(g.user_claims)
        return jsonify({"items": list_voyages(user["id"])})

    @app.get("/api/voyages/<int:voyage_id>")
    @require_auth
    def voyage(voyage_id):
        user = ensure_user(g.user_claims)
        item = get_voyage(voyage_id, user["id"])
        if not item:
            return jsonify({"error": "Voyage not found"}), 404
        return jsonify(item)

    @app.post("/api/voyages/<int:voyage_id>/offline-pack")
    @require_auth
    def offline_pack(voyage_id):
        user = ensure_user(g.user_claims)
        voyage_item = get_voyage(voyage_id, user["id"])
        if not voyage_item:
            return jsonify({"error": "Voyage not found"}), 404

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        pack = {
            "voyage_id": voyage_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": expires_at,
            "origin": {
                "label": voyage_item.get("origin_label"),
                "lat": voyage_item["origin_lat"],
                "lon": voyage_item["origin_lon"],
            },
            "destination": {
                "label": voyage_item.get("destination_label"),
                "lat": voyage_item["destination_lat"],
                "lon": voyage_item["destination_lon"],
            },
            "gemini_plan": voyage_item["gemini_plan"],
            "waypoints": voyage_item["waypoints"],
            "noaa_snapshot": voyage_item["noaa_snapshot"],
            "usage_note": "This pack is a 24-hour decision-support snapshot. Check official weather again when online.",
        }
        return jsonify(create_offline_pack(user["id"], voyage_id, expires_at, pack)), 201

    return app


def _missing(payload, fields):
    return [field for field in fields if field not in payload]


def _point(value):
    if not isinstance(value, dict):
        raise ValueError("Point must be an object with lat and lon")
    try:
        lat = float(value["lat"])
        lon = float(value["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Point must include numeric lat and lon") from exc
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Latitude or longitude is out of range")
    return {"lat": lat, "lon": lon}


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=port, debug=os.getenv("FLASK_ENV") == "development")
