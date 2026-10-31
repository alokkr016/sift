"""Move or trash indexed photos. Both require an indexed id and a caller confirmation."""

import shutil
import sqlite3
from pathlib import Path

from sift.access import allowed_file


class ActionError(Exception):
    pass


def forget(connection: sqlite3.Connection, file_id: int) -> None:
    group = connection.execute(
        "SELECT group_key FROM dup_groups WHERE file_id = ?",
        (file_id,),
    ).fetchone()
    connection.execute("DELETE FROM faces WHERE file_id = ?", (file_id,))
    connection.execute("DELETE FROM dup_groups WHERE file_id = ?", (file_id,))
    if group is not None:
        left = connection.execute(
            "SELECT COUNT(*) FROM dup_groups WHERE group_key = ?",
            (group["group_key"],),
        ).fetchone()[0]
        if left < 2:
            connection.execute(
                "DELETE FROM dup_groups WHERE group_key = ?",
                (group["group_key"],),
            )
    connection.execute("DELETE FROM files WHERE id = ?", (file_id,))


def trash_file(path: Path) -> str:
    from Foundation import NSURL, NSFileManager

    url = NSURL.fileURLWithPath_(str(path))
    result = NSFileManager.defaultManager().trashItemAtURL_resultingItemURL_error_(url, None, None)
    ok = result[0] if isinstance(result, tuple) else bool(result)
    if not ok:
        detail = result[-1] if isinstance(result, tuple) else "Finder refused the Trash"
        raise ActionError(str(detail))
    trashed = result[1] if isinstance(result, tuple) and result[1] is not None else path
    return str(trashed)


def trash_indexed(connection: sqlite3.Connection, file_id: int) -> str:
    path = allowed_file(connection, file_id)
    if path is None:
        raise ActionError("that photo is not in the index")
    trashed = trash_file(path)
    forget(connection, file_id)
    return trashed


def trash_other_copies(connection: sqlite3.Connection, file_id: int) -> dict:
    path = allowed_file(connection, file_id)
    if path is None:
        raise ActionError("that photo is not in the index")
    group = connection.execute(
        "SELECT group_key FROM dup_groups WHERE file_id = ?",
        (file_id,),
    ).fetchone()
    if group is None:
        return {"trashed": 0, "failed": 0}
    others = connection.execute(
        "SELECT file_id FROM dup_groups WHERE group_key = ? AND file_id != ?",
        (group["group_key"], file_id),
    ).fetchall()
    trashed = 0
    failed = 0
    for row in others:
        try:
            trash_indexed(connection, row["file_id"])
            trashed += 1
        except (ActionError, OSError):
            failed += 1
    return {"trashed": trashed, "failed": failed}


def move_indexed(connection: sqlite3.Connection, file_id: int, destination: Path) -> str:
    path = allowed_file(connection, file_id)
    if path is None:
        raise ActionError("that photo is not in the index")
    folder = Path(destination).expanduser().resolve()
    if not folder.is_dir():
        raise ActionError("pick an existing folder")
    target = _unique_target(folder, path.name, file_id)
    if target.resolve() == path.resolve():
        return str(path)
    shutil.move(path, target)
    stat = target.stat()
    connection.execute("INSERT OR IGNORE INTO roots(path) VALUES (?)", (str(folder),))
    connection.execute(
        "UPDATE files SET path = ?, size = ?, mtime = ? WHERE id = ?",
        (str(target.resolve()), stat.st_size, stat.st_mtime, file_id),
    )
    return str(target.resolve())


def reveal(connection: sqlite3.Connection, file_id: int) -> None:
    import subprocess

    path = allowed_file(connection, file_id)
    if path is None:
        raise ActionError("that photo is not in the index")
    subprocess.run(["open", "-R", str(path)], check=False)


def _unique_target(folder: Path, name: str, file_id: int) -> Path:
    candidate = folder / name
    if not candidate.exists():
        return candidate
    stem = Path(name).stem
    suffix = Path(name).suffix
    return folder / f"{stem}-{file_id}{suffix}"
