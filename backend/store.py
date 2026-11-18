"""SQLite-backed session store: imagery, detections, and an append-only review log.

One file per session directory. Review decisions are written before the API
responds, so a restart or crash loses nothing, and every status change is kept
in ``review_log`` with who made it and when.
"""
from __future__ import annotations

import datetime as _dt
import json
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 1
STATUSES = ("pending", "confirmed", "rejected", "unsure")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    file TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    model TEXT,
    uploaded_utc TEXT NOT NULL,
    n_detections INTEGER NOT NULL,
    lat REAL, lon REAL, gsd_m REAL,
    geo TEXT,       -- JSON: georeferencing method, input sources, warnings
    bounds TEXT     -- JSON: [[south, west], [north, east]]
);
CREATE TABLE IF NOT EXISTS detections (
    id TEXT PRIMARY KEY,
    image_id TEXT NOT NULL REFERENCES images(id),
    image TEXT NOT NULL,
    x1 REAL NOT NULL, y1 REAL NOT NULL, x2 REAL NOT NULL, y2 REAL NOT NULL,
    conf REAL NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    lon REAL, lat REAL,
    position_quality TEXT,
    reviewed_by TEXT,
    reviewed_utc TEXT,
    extra TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS review_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_id TEXT NOT NULL REFERENCES detections(id),
    from_status TEXT NOT NULL,
    to_status TEXT NOT NULL,
    analyst TEXT NOT NULL,
    at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS detections_image ON detections(image_id);
"""

_DETECTION_COLUMNS = ("id", "image_id", "image", "x1", "y1", "x2", "y2", "conf", "label",
                      "status", "lon", "lat", "position_quality", "extra")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            found = conn.execute("PRAGMA user_version").fetchone()[0]
            if found > SCHEMA_VERSION:
                raise RuntimeError(
                    f"{self.path} was written by a newer Survey Signal (schema {found})."
                )
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # --- writes --------------------------------------------------------------
    def add_image(self, image: dict, detections: list[dict]) -> dict:
        """Record one processed image and its proposals in a single transaction."""
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO images (id, file, sha256, model, uploaded_utc, n_detections, lat, "
                "lon, gsd_m, geo, bounds) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (image["id"], image["file"], image["sha256"], image.get("model"), _now(),
                 len(detections), image.get("lat"), image.get("lon"), image.get("gsd_m"),
                 json.dumps(image.get("geo")), json.dumps(image.get("bounds"))),
            )
            conn.executemany(
                f"INSERT INTO detections ({', '.join(_DETECTION_COLUMNS)}) "
                f"VALUES ({', '.join('?' * len(_DETECTION_COLUMNS))})",
                [tuple(json.dumps(d.get("extra") or {}) if c == "extra"
                       else d.get(c, "pending") if c == "status" else d.get(c)
                       for c in _DETECTION_COLUMNS) for d in detections],
            )
        return self.image(image["id"])

    def set_status(self, detection_id: str, status: str, analyst: str) -> dict | None:
        """Change a review decision and append it to the audit log."""
        if status not in STATUSES:
            raise ValueError(f"bad status: {status}")
        analyst = (analyst or "").strip() or "unspecified"
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT status FROM detections WHERE id = ?",
                               (detection_id,)).fetchone()
            if row is None:
                return None
            now = _now()
            conn.execute(
                "UPDATE detections SET status = ?, reviewed_by = ?, reviewed_utc = ? WHERE id = ?",
                (status, analyst, now, detection_id),
            )
            conn.execute(
                "INSERT INTO review_log (detection_id, from_status, to_status, analyst, at_utc) "
                "VALUES (?, ?, ?, ?, ?)", (detection_id, row["status"], status, analyst, now),
            )
        return self.detection(detection_id)

    # --- reads ---------------------------------------------------------------
    @staticmethod
    def _image_row(row: sqlite3.Row) -> dict:
        out = dict(row)
        out["geo"] = json.loads(out["geo"]) if out["geo"] else None
        out["bounds"] = json.loads(out["bounds"]) if out["bounds"] else None
        return out

    @staticmethod
    def _detection_row(row: sqlite3.Row) -> dict:
        out = dict(row)
        out["extra"] = json.loads(out["extra"])
        return out

    def images(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM images ORDER BY uploaded_utc, id").fetchall()
        return [self._image_row(r) for r in rows]

    def image(self, image_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        return self._image_row(row) if row else None

    def detections(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM detections ORDER BY conf DESC, id").fetchall()
        return [self._detection_row(r) for r in rows]

    def detection(self, detection_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM detections WHERE id = ?",
                               (detection_id,)).fetchone()
        return self._detection_row(row) if row else None

    def review_log(self) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM review_log ORDER BY seq").fetchall()
        return [dict(r) for r in rows]
