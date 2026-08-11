import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app.config import DB_PATH, DEFAULT_SETTINGS

_SCHEMA_FILE = Path(__file__).with_name("schema.sql")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columnas añadidas después de la primera versión. Se aplican sobre bases de
# datos ya creadas sin perder los datos existentes.
_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "clients": [
        ("estado_civil", "TEXT"),
        ("regimen_economico", "TEXT"),
        ("tiene_hijos", "INTEGER NOT NULL DEFAULT 0"),
        ("num_hijos", "INTEGER NOT NULL DEFAULT 0"),
        ("tiene_vehiculos", "INTEGER NOT NULL DEFAULT 0"),
        ("tiene_cuentas", "INTEGER NOT NULL DEFAULT 0"),
        ("tiene_hipotecas", "INTEGER NOT NULL DEFAULT 0"),
        ("tiene_propiedades", "INTEGER NOT NULL DEFAULT 0"),
        ("tiene_deudas", "INTEGER NOT NULL DEFAULT 0"),
    ],
}


def _migrate(conn: sqlite3.Connection) -> None:
    for table, columns in _MIGRATIONS.items():
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if not existing:
            continue  # la tabla aún no existe; el schema la crea completa
        for name, decl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def init_db() -> None:
    conn = get_connection()
    try:
        with open(_SCHEMA_FILE, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        _migrate(conn)
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    try:
        return conn.execute(query, tuple(params)).fetchall()
    finally:
        conn.close()


def fetch_one(query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    conn = get_connection()
    try:
        return conn.execute(query, tuple(params)).fetchone()
    finally:
        conn.close()


def execute(query: str, params: Iterable[Any] = ()) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(query, tuple(params))
        conn.commit()
        return cur.lastrowid or cur.rowcount
    finally:
        conn.close()


def execute_many(query: str, seq: Iterable[Iterable[Any]]) -> None:
    conn = get_connection()
    try:
        conn.executemany(query, [tuple(p) for p in seq])
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str, default: str | None = None) -> str | None:
    row = fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
    if row is None:
        return default
    return row["value"]


def set_setting(key: str, value: str) -> None:
    execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
