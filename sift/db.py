import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL UNIQUE,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    width INTEGER,
    height INTEGER,
    has_camera INTEGER NOT NULL DEFAULT 0,
    is_screenshot INTEGER NOT NULL DEFAULT 0,
    dhash TEXT,
    label TEXT,
    scanned_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dup_groups (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    group_key TEXT NOT NULL,
    UNIQUE(file_id)
);

CREATE TABLE IF NOT EXISTS roots (
    path TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS faces (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    w REAL NOT NULL,
    h REAL NOT NULL,
    feature BLOB,
    person_key TEXT,
    FOREIGN KEY(file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS people (
    person_key TEXT PRIMARY KEY,
    name TEXT
);

CREATE INDEX IF NOT EXISTS files_label ON files(label);
CREATE INDEX IF NOT EXISTS dup_groups_key ON dup_groups(group_key);
CREATE INDEX IF NOT EXISTS faces_file ON faces(file_id);
CREATE INDEX IF NOT EXISTS faces_person ON faces(person_key);
"""


def migrate(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(files)")}
    if "faces_scanned" not in columns:
        connection.execute(
            "ALTER TABLE files ADD COLUMN faces_scanned INTEGER NOT NULL DEFAULT 0"
        )


def connect(db_path: Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch(mode=0o600)
    previous = os.umask(0o077)
    try:
        connection = sqlite3.connect(db_path, timeout=30)
    finally:
        os.umask(previous)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(SCHEMA)
    migrate(connection)
    os.chmod(db_path, 0o600)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            os.chmod(sidecar, 0o600)
    return connection


def default_db() -> Path:
    return Path.home() / "Library" / "Application Support" / "Sift" / "sift.sqlite"
