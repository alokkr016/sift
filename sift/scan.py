"""Walk a folder and index images. Files are never moved or deleted."""

import time
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from sift.db import connect
from sift.duplicates import rebuild_groups

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
_MAKE = 271
_MODEL = 272
_DATE_TIME_ORIGINAL = 36867
_EXIF_IFD = 0x8769


def looks_like_screenshot(path: Path, width: int, height: int, has_camera: bool, has_taken: bool) -> bool:
    name = path.name.lower().replace("_", " ").replace("-", " ")
    if "screenshot" in name or "screen shot" in name:
        return True
    if path.suffix.lower() != ".png" or has_camera or has_taken or width <= 0 or height <= 0:
        return False
    long_side = max(width, height)
    short_side = min(width, height)
    aspect = long_side / short_side
    return 1.7 <= aspect <= 2.4


def _exif_flags(image: Image.Image) -> tuple[bool, bool]:
    exif = image.getexif()
    if not exif:
        return False, False
    make = exif.get(_MAKE) or ""
    model = exif.get(_MODEL) or ""
    taken = exif.get(_DATE_TIME_ORIGINAL) or ""
    try:
        nested = exif.get_ifd(_EXIF_IFD)
    except KeyError:
        nested = {}
    taken = taken or nested.get(_DATE_TIME_ORIGINAL) or ""
    has_camera = bool(str(make).strip() or str(model).strip())
    has_taken = bool(str(taken).strip())
    return has_camera, has_taken


def _hash_image(image: Image.Image) -> str | None:
    import imagehash

    try:
        return str(imagehash.dhash(image))
    except Exception:
        return None


def index_file(path: Path) -> dict | None:
    try:
        with Image.open(path) as image:
            image.load()
            width, height = image.size
            has_camera, has_taken = _exif_flags(image)
            digest = _hash_image(image)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        return None
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "mtime": stat.st_mtime,
        "width": width,
        "height": height,
        "has_camera": int(has_camera),
        "is_screenshot": int(looks_like_screenshot(path, width, height, has_camera, has_taken)),
        "dhash": digest,
        "scanned_at": time.time(),
    }


def scan_folder(folder: Path, db_path: Path) -> dict:
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise NotADirectoryError(str(folder))
    connection = connect(db_path)
    try:
        connection.execute("INSERT OR IGNORE INTO roots(path) VALUES (?)", (str(folder),))
        seen = 0
        added = 0
        updated = 0
        skipped = 0
        unreadable = 0
        for path in _images(folder):
            seen += 1
            stat = path.stat()
            resolved = str(path.resolve())
            row = connection.execute(
                "SELECT size, mtime FROM files WHERE path = ?",
                (resolved,),
            ).fetchone()
            if row and row["size"] == stat.st_size and row["mtime"] == stat.st_mtime:
                skipped += 1
                continue
            record = index_file(path)
            if record is None:
                unreadable += 1
                continue
            if row is None:
                connection.execute(
                    """
                    INSERT INTO files(path, size, mtime, width, height, has_camera, is_screenshot, dhash, scanned_at)
                    VALUES (:path, :size, :mtime, :width, :height, :has_camera, :is_screenshot, :dhash, :scanned_at)
                    """,
                    record,
                )
                added += 1
            else:
                connection.execute(
                    """
                    UPDATE files
                    SET size = :size, mtime = :mtime, width = :width, height = :height,
                        has_camera = :has_camera, is_screenshot = :is_screenshot,
                        dhash = :dhash, scanned_at = :scanned_at
                    WHERE path = :path
                    """,
                    record,
                )
                updated += 1
            if seen % 200 == 0:
                connection.commit()
                print(f"scanned {seen}", flush=True)
        groups = rebuild_groups(connection)
        connection.commit()
        return {
            "seen": seen,
            "added": added,
            "updated": updated,
            "unchanged": skipped,
            "unreadable": unreadable,
            "duplicate_groups": groups,
        }
    finally:
        connection.close()


def _images(folder: Path):
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.lower() in IMAGE_SUFFIXES:
            yield path
