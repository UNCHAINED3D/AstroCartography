"""
Birth-entry persistence.

Stores user-saved birth entries (name + birth data) in a small SQLite database
so charts can be reloaded later without re-typing everything. Uses only the
Python standard library so no extra dependency is required.

The DB file lives next to this module by default (``births.db``); override with
the ``BIRTHS_DB`` environment variable.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

_DB_PATH = os.environ.get("BIRTHS_DB") or str(Path(__file__).parent / "births.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _init() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS births (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                datetime TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "datetime": row["datetime"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
        "note": row["note"],
        "created_at": row["created_at"],
    }


def create_entry(
    name: str,
    datetime: str,
    latitude: float,
    longitude: float,
    note: Optional[str] = None,
) -> dict[str, Any]:
    _init()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO births (name, datetime, latitude, longitude, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, datetime, latitude, longitude, note),
        )
        row = conn.execute(
            "SELECT * FROM births WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _row_to_dict(row)


def list_entries() -> list[dict[str, Any]]:
    _init()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM births ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_entry(entry_id: int) -> Optional[dict[str, Any]]:
    _init()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM births WHERE id = ?", (entry_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def update_entry(
    entry_id: int,
    name: Optional[str] = None,
    datetime: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    note: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    _init()
    fields: list[str] = []
    values: list[Any] = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if datetime is not None:
        fields.append("datetime = ?")
        values.append(datetime)
    if latitude is not None:
        fields.append("latitude = ?")
        values.append(latitude)
    if longitude is not None:
        fields.append("longitude = ?")
        values.append(longitude)
    if note is not None:
        fields.append("note = ?")
        values.append(note)
    if not fields:
        return get_entry(entry_id)
    values.append(entry_id)
    with _connect() as conn:
        conn.execute(
            f"UPDATE births SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM births WHERE id = ?", (entry_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def delete_entry(entry_id: int) -> bool:
    _init()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM births WHERE id = ?", (entry_id,))
    return cur.rowcount > 0
