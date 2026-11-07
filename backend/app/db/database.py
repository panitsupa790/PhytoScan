from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_migration_lock = threading.Lock()


def resolve_database_path(database_path: str | Path | None = None) -> Path:
    configured = Path(database_path or settings.database_path)
    if configured.is_absolute():
        return configured.resolve()
    return (BACKEND_ROOT / configured).resolve()


def connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = resolve_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def database_connection(
    database_path: str | Path | None = None,
) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
    finally:
        connection.close()


def apply_migrations(database_path: str | Path | None = None) -> None:
    with _migration_lock, database_connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        connection.commit()
        applied = {
            int(row["version"])
            for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for migration_path in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(migration_path.name.split("_", 1)[0])
            if version in applied:
                continue
            name = migration_path.stem.replace("'", "''")
            sql = migration_path.read_text(encoding="utf-8")
            script = (
                "BEGIN IMMEDIATE;\n"
                f"{sql}\n"
                "INSERT INTO schema_migrations(version, name, applied_at) "
                f"VALUES ({version}, '{name}', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'));\n"
                "COMMIT;"
            )
            try:
                connection.executescript(script)
            except sqlite3.Error:
                if connection.in_transaction:
                    connection.rollback()
                raise


def initialize_database(
    database_path: str | Path | None = None,
    *,
    seed: bool = True,
) -> Path:
    path = resolve_database_path(database_path)
    apply_migrations(path)
    if seed:
        from app.db.seed import seed_reference_data

        seed_reference_data(path)
    return path
