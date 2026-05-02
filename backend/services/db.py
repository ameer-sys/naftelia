import json
import os
import sqlite3
from pathlib import Path

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parents[1]
DB_URL = os.getenv("DATABASE_URL")
FLASK_ENV = os.getenv("FLASK_ENV", "development")

# Determine if using PostgreSQL or SQLite
USE_POSTGRES = FLASK_ENV == "production" and DB_URL and PSYCOPG2_AVAILABLE

if not USE_POSTGRES:
    DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "instance" / "naftelia.sqlite3"))


class DBConnection:
    """Context manager that handles both SQLite and PostgreSQL connections."""
    
    def __init__(self):
        self.conn = None
        self.is_postgres = USE_POSTGRES
    
    def __enter__(self):
        if self.is_postgres:
            self.conn = psycopg2.connect(DB_URL)
            self.conn.autocommit = False
        else:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(DB_PATH)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()
            self.conn.close()


def get_connection():
    """Get a database connection (for direct use without context manager)."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        return conn
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def init_db():
    """Initialize database schema."""
    if USE_POSTGRES:
        # PostgreSQL schema
        schema_stmts = [
            """
            CREATE TABLE IF NOT EXISTS users (
              id SERIAL PRIMARY KEY,
              auth0_sub TEXT NOT NULL UNIQUE,
              email TEXT,
              full_name TEXT,
              home_port TEXT,
              preferred_units TEXT DEFAULT 'metric',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS vessels (
              id SERIAL PRIMARY KEY,
              user_id INTEGER NOT NULL,
              name TEXT,
              vessel_type TEXT NOT NULL,
              length_m REAL,
              draft_m REAL,
              cruising_speed_kn REAL,
              safety_margin TEXT DEFAULT 'balanced',
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS voyage_plans (
              id SERIAL PRIMARY KEY,
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
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
              FOREIGN KEY (vessel_id) REFERENCES vessels(id) ON DELETE SET NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS route_waypoints (
              id SERIAL PRIMARY KEY,
              voyage_id INTEGER NOT NULL,
              sequence INTEGER NOT NULL,
              label TEXT,
              latitude REAL NOT NULL,
              longitude REAL NOT NULL,
              instruction TEXT,
              caution_level TEXT DEFAULT 'normal',
              FOREIGN KEY (voyage_id) REFERENCES voyage_plans(id) ON DELETE CASCADE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS offline_packs (
              id SERIAL PRIMARY KEY,
              voyage_id INTEGER NOT NULL,
              user_id INTEGER NOT NULL,
              expires_at TIMESTAMP NOT NULL,
              pack_json TEXT NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (voyage_id) REFERENCES voyage_plans(id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        ]
        
        try:
            conn = psycopg2.connect(DB_URL)
            cursor = conn.cursor()
            for stmt in schema_stmts:
                if stmt.strip():
                    cursor.execute(stmt)
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")
            raise
    else:
        # SQLite schema
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
    """Convert database row to dict."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


def ensure_user(claims, payload=None):
    payload = payload or {}
    auth0_sub = claims.get("sub", "demo-captain")
    email = payload.get("email") or claims.get("email")
    full_name = payload.get("full_name") or payload.get("name") or claims.get("name")
    
    with DBConnection() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                """
                INSERT INTO users (auth0_sub, email, full_name, home_port, preferred_units)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (auth0_sub) DO UPDATE SET
                  email = COALESCE(EXCLUDED.email, users.email),
                  full_name = COALESCE(EXCLUDED.full_name, users.full_name),
                  home_port = COALESCE(EXCLUDED.home_port, users.home_port),
                  preferred_units = COALESCE(EXCLUDED.preferred_units, users.preferred_units),
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
            cursor.execute("SELECT * FROM users WHERE auth0_sub = %s", (auth0_sub,))
            user = _dict(cursor.fetchone())
            conn.commit()
        else:
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
            user = _dict(conn.execute("SELECT * FROM users WHERE auth0_sub = ?", (auth0_sub,)).fetchone())
    
    return user


def upsert_vessel(user_id, payload):
    with DBConnection() as conn:
        vessel_id = payload.get("id")
        
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            if vessel_id:
                cursor.execute(
                    """
                    UPDATE vessels SET
                      name = %s, vessel_type = %s, length_m = %s, draft_m = %s,
                      cruising_speed_kn = %s, safety_margin = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND user_id = %s
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
                cursor.execute(
                    """
                    INSERT INTO vessels
                      (user_id, name, vessel_type, length_m, draft_m, cruising_speed_kn, safety_margin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
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
                vessel_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT * FROM vessels WHERE id = %s", (vessel_id,))
            vessel = _dict(cursor.fetchone())
            conn.commit()
        else:
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
            
            vessel = _dict(conn.execute("SELECT * FROM vessels WHERE id = ?", (vessel_id,)).fetchone())
    
    return vessel


def list_vessels(user_id):
    with DBConnection() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute("SELECT * FROM vessels WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
            rows = conn.execute("SELECT * FROM vessels WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()
            return [dict(row) for row in rows]


def create_voyage(user_id, payload, noaa_snapshot, gemini_plan):
    waypoints = gemini_plan.get("waypoints") or []
    
    with DBConnection() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                """
                INSERT INTO voyage_plans
                  (user_id, vessel_id, origin_label, origin_lat, origin_lon,
                   destination_label, destination_lat, destination_lon,
                   departure_time, noaa_snapshot_json, gemini_plan_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
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
            voyage_id = cursor.fetchone()[0]
            
            for index, waypoint in enumerate(waypoints):
                cursor.execute(
                    """
                    INSERT INTO route_waypoints
                      (voyage_id, sequence, label, latitude, longitude, instruction, caution_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            conn.commit()
        else:
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
    
    return get_voyage(voyage_id, user_id)


def get_voyage(voyage_id, user_id, conn=None):
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    
    try:
        if USE_POSTGRES and isinstance(conn, psycopg2.extensions.connection):
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                "SELECT * FROM voyage_plans WHERE id = %s AND user_id = %s",
                (voyage_id, user_id),
            )
            voyage = _dict(cursor.fetchone())
            
            if not voyage:
                return None
            
            voyage["noaa_snapshot"] = json.loads(voyage.pop("noaa_snapshot_json"))
            voyage["gemini_plan"] = json.loads(voyage.pop("gemini_plan_json"))
            
            cursor.execute(
                "SELECT label, latitude, longitude, instruction, caution_level FROM route_waypoints WHERE voyage_id = %s ORDER BY sequence",
                (voyage_id,),
            )
            waypoint_rows = cursor.fetchall()
            voyage["waypoints"] = [dict(item) for item in waypoint_rows]
        else:
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
    with DBConnection() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cursor.execute(
                """
                SELECT id, origin_label, destination_label, departure_time, status, created_at
                FROM voyage_plans
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        else:
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
    with DBConnection() as conn:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO offline_packs (voyage_id, user_id, expires_at, pack_json)
                VALUES (%s, %s, %s, %s)
                """,
                (voyage_id, user_id, expires_at, json.dumps(pack)),
            )
            conn.commit()
        else:
            conn.execute(
                """
                INSERT INTO offline_packs (voyage_id, user_id, expires_at, pack_json)
                VALUES (?, ?, ?, ?)
                """,
                (voyage_id, user_id, expires_at, json.dumps(pack)),
            )
    
    return pack
