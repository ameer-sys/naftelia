import json
import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "instance" / "naftelia.sqlite3"))


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              auth0_sub TEXT NOT NULL UNIQUE,
              email TEXT,
              full_name TEXT,
              home_port TEXT,
              preferred_units TEXT DEFAULT 'metric',
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vessels (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              name TEXT,
              vessel_type TEXT NOT NULL,
              length_m REAL,
              draft_m REAL,
              cruising_speed_kn REAL,
              safety_margin TEXT DEFAULT 'balanced',
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS voyage_plans (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              vessel_id INTEGER,
              origin_label TEXT,
              origin_lat REAL NOT NULL,
              origin_lon REAL NOT NULL,
              destination_label TEXT,
              destination_lat REAL NOT NULL,
              destination_lon REAL NOT NULL,
              departure_time TEXT,
              status TEXT DEFAULT 'planned',
              noaa_snapshot_json TEXT NOT NULL,
              gemini_plan_json TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
              FOREIGN KEY (vessel_id) REFERENCES vessels(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS route_waypoints (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              voyage_id INTEGER NOT NULL,
              sequence INTEGER NOT NULL,
              label TEXT,
              latitude REAL NOT NULL,
              longitude REAL NOT NULL,
              instruction TEXT,
              caution_level TEXT DEFAULT 'normal',
              FOREIGN KEY (voyage_id) REFERENCES voyage_plans(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS offline_packs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              voyage_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              expires_at TEXT NOT NULL,
              pack_json TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (voyage_id) REFERENCES voyage_plans(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def _dict(row):
    return dict(row) if row else None


def ensure_user(claims, payload=None):
    payload = payload or {}
    auth0_sub = claims.get("sub", "demo-captain")
    email = payload.get("email") or claims.get("email")
    full_name = payload.get("full_name") or payload.get("name") or claims.get("name")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (auth0_sub, email, full_name, home_port, preferred_units)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(auth0_sub) DO UPDATE SET
              email = COALESCE(excluded.email, users.email),
              full_name = COALESCE(excluded.full_name, users.full_name),
              home_port = COALESCE(excluded.home_port, users.home_port),
              preferred_units = COALESCE(excluded.preferred_units, users.preferred_units),
              updated_at = CURRENT_TIMESTAMP
            """,
            (
                auth0_sub,
                email,
                full_name,
                payload.get("home_port"),
                payload.get("preferred_units", "metric"),
            ),
        )
        return _dict(conn.execute("SELECT * FROM users WHERE auth0_sub = ?", (auth0_sub,)).fetchone())


def upsert_vessel(user_id, payload):
    with get_connection() as conn:
        vessel_id = payload.get("id")
        if vessel_id:
            conn.execute(
                """
                UPDATE vessels SET
                  name = ?, vessel_type = ?, length_m = ?, draft_m = ?,
                  cruising_speed_kn = ?, safety_margin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND user_id = ?
                """,
                (
                    payload.get("name"),
                    payload.get("vessel_type", "Sailboat"),
                    payload.get("length_m"),
                    payload.get("draft_m"),
                    payload.get("cruising_speed_kn"),
                    payload.get("safety_margin", "balanced"),
                    vessel_id,
                    user_id,
                ),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO vessels
                  (user_id, name, vessel_type, length_m, draft_m, cruising_speed_kn, safety_margin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    payload.get("name"),
                    payload.get("vessel_type", "Sailboat"),
                    payload.get("length_m"),
                    payload.get("draft_m"),
                    payload.get("cruising_speed_kn"),
                    payload.get("safety_margin", "balanced"),
                ),
            )
            vessel_id = cursor.lastrowid
        return _dict(conn.execute("SELECT * FROM vessels WHERE id = ?", (vessel_id,)).fetchone())


def list_vessels(user_id):
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM vessels WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
        return [dict(row) for row in rows]


def create_voyage(user_id, payload, noaa_snapshot, gemini_plan):
    waypoints = gemini_plan.get("waypoints") or []
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO voyage_plans
              (user_id, vessel_id, origin_label, origin_lat, origin_lon,
               destination_label, destination_lat, destination_lon,
               departure_time, noaa_snapshot_json, gemini_plan_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                payload.get("vessel_id"),
                payload.get("origin_label"),
                payload["origin"]["lat"],
                payload["origin"]["lon"],
                payload.get("destination_label"),
                payload["destination"]["lat"],
                payload["destination"]["lon"],
                payload.get("departure_time"),
                json.dumps(noaa_snapshot),
                json.dumps(gemini_plan),
            ),
        )
        voyage_id = cursor.lastrowid
        for index, waypoint in enumerate(waypoints):
            conn.execute(
                """
                INSERT INTO route_waypoints
                  (voyage_id, sequence, label, latitude, longitude, instruction, caution_level)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    voyage_id,
                    index,
                    waypoint.get("label"),
                    waypoint["lat"],
                    waypoint["lon"],
                    waypoint.get("instruction"),
                    waypoint.get("caution_level", "normal"),
                ),
            )
        return get_voyage(voyage_id, user_id, conn)


def get_voyage(voyage_id, user_id, conn=None):
    owns_conn = conn is None
    conn = conn or get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM voyage_plans WHERE id = ? AND user_id = ?",
            (voyage_id, user_id),
        ).fetchone()
        voyage = _dict(row)
        if not voyage:
            return None
        voyage["noaa_snapshot"] = json.loads(voyage.pop("noaa_snapshot_json"))
        voyage["gemini_plan"] = json.loads(voyage.pop("gemini_plan_json"))
        waypoint_rows = conn.execute(
            "SELECT label, latitude, longitude, instruction, caution_level FROM route_waypoints WHERE voyage_id = ? ORDER BY sequence",
            (voyage_id,),
        ).fetchall()
        voyage["waypoints"] = [dict(item) for item in waypoint_rows]
        return voyage
    finally:
        if owns_conn:
            conn.close()


def list_voyages(user_id, limit=20):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, origin_label, destination_label, departure_time, status, created_at
            FROM voyage_plans
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def create_offline_pack(user_id, voyage_id, expires_at, pack):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO offline_packs (voyage_id, user_id, expires_at, pack_json)
            VALUES (?, ?, ?, ?)
            """,
            (voyage_id, user_id, expires_at, json.dumps(pack)),
        )
        return pack
