"""Decide which indexed files the app is allowed to open."""

from pathlib import Path


def allowed_file(connection, file_id: int) -> Path | None:
    row = connection.execute("SELECT path FROM files WHERE id = ?", (file_id,)).fetchone()
    if row is None:
        return None
    candidate = Path(row["path"]).resolve()
    if not candidate.is_file() or candidate.is_symlink():
        return None
    roots = [Path(item["path"]).resolve() for item in connection.execute("SELECT path FROM roots")]
    for root in roots:
        try:
            candidate.relative_to(root)
            return candidate
        except ValueError:
            continue
    return None
