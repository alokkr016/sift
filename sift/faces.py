"""On-device face grouping with Apple's Vision framework.

Faces never leave this Mac. A group means two face crops look alike to Vision's
image feature print. It is a hint you can name. It is not a police-style match.
"""

import io
import sqlite3
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

# Cosine distance. Lower is more alike. 0.34 kept same-person crops together
# in local checks without merging obviously different crops.
MATCH_DISTANCE = 0.34


def crop_box(width: int, height: int, x: float, y: float, w: float, h: float, pad: float = 0.25):
    """Vision boxes are normalized with a bottom-left origin. Return a pixel box."""
    pixel_w = max(1, int(w * width))
    pixel_h = max(1, int(h * height))
    left = int(x * width)
    top = int((1.0 - y - h) * height)
    grow_x = int(pixel_w * pad)
    grow_y = int(pixel_h * pad)
    left = max(0, left - grow_x)
    top = max(0, top - grow_y)
    right = min(width, left + pixel_w + grow_x * 2)
    bottom = min(height, top + pixel_h + grow_y * 2)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _feature_print(image: Image.Image) -> np.ndarray | None:
    import Vision
    from Foundation import NSData

    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=90)
    data = NSData.dataWithBytes_length_(buffer.getvalue(), len(buffer.getvalue()))
    request = Vision.VNGenerateImageFeaturePrintRequest.alloc().init()
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(data, None)
    ok, _error = handler.performRequests_error_([request], None)
    if not ok:
        return None
    results = request.results() or []
    if not results:
        return None
    observation = results[0]
    raw = bytes(observation.data())
    count = int(observation.elementCount())
    if count <= 0 or len(raw) < count * 4:
        return None
    vector = np.frombuffer(raw[: count * 4], dtype="<f4").astype(np.float32)
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return None
    return vector / norm


def _detect_boxes(path: Path) -> list[tuple[float, float, float, float]]:
    import Vision
    from Foundation import NSURL

    url = NSURL.fileURLWithPath_(str(path))
    request = Vision.VNDetectFaceRectanglesRequest.alloc().init()
    handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
    ok, _error = handler.performRequests_error_([request], None)
    if not ok:
        return []
    boxes = []
    for face in request.results() or []:
        box = face.boundingBox()
        boxes.append((float(box.origin.x), float(box.origin.y), float(box.size.width), float(box.size.height)))
    return boxes


def index_faces(path: Path) -> list[dict]:
    boxes = _detect_boxes(path)
    if not boxes:
        return []
    with Image.open(path) as image:
        oriented = ImageOps.exif_transpose(image)
        width, height = oriented.size
        found = []
        for x, y, w, h in boxes:
            pixels = crop_box(width, height, x, y, w, h)
            if pixels is None:
                continue
            crop = oriented.crop(pixels)
            if min(crop.size) < 24:
                continue
            feature = _feature_print(crop)
            if feature is None:
                continue
            found.append({
                "x": x,
                "y": y,
                "w": w,
                "h": h,
                "feature": feature.tobytes(),
            })
        return found


def scan_faces(db_path: Path, progress=print) -> dict:
    from sift.access import allowed_file
    from sift.db import connect

    connection = connect(db_path)
    added = 0
    photos = 0
    failed = 0
    try:
        rows = connection.execute(
            "SELECT id FROM files WHERE faces_scanned = 0 ORDER BY id"
        ).fetchall()
        total = len(rows)
        for index, row in enumerate(rows, start=1):
            path = allowed_file(connection, row["id"])
            photos += 1
            try:
                faces = index_faces(path) if path is not None else []
            except (OSError, ValueError):
                faces = []
                failed += 1
            connection.execute("DELETE FROM faces WHERE file_id = ?", (row["id"],))
            for face in faces:
                connection.execute(
                    """
                    INSERT INTO faces(file_id, x, y, w, h, feature)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (row["id"], face["x"], face["y"], face["w"], face["h"], face["feature"]),
                )
                added += 1
            connection.execute(
                "UPDATE files SET faces_scanned = 1 WHERE id = ?",
                (row["id"],),
            )
            if index % 25 == 0:
                connection.commit()
                progress(f"faces {index}/{total}, found {added}")
        grouped = assign_people(connection)
        connection.commit()
        return {"photos": photos, "faces": added, "failed": failed, "people": grouped}
    finally:
        connection.close()


def assign_people(connection: sqlite3.Connection, threshold: float = MATCH_DISTANCE) -> int:
    rows = connection.execute(
        "SELECT id, feature, person_key FROM faces WHERE feature IS NOT NULL"
    ).fetchall()
    if not rows:
        return 0
    vectors = []
    ids = []
    keys = []
    for row in rows:
        vector = np.frombuffer(row["feature"], dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        if norm == 0 or vector.size < 8:
            continue
        vectors.append(vector / norm)
        ids.append(row["id"])
        keys.append(row["person_key"])
    if not vectors:
        return 0
    matrix = np.vstack(vectors)
    centroids: dict[str, np.ndarray] = {}
    counts: dict[str, int] = {}
    for key, vector in zip(keys, matrix):
        if not key:
            continue
        if key in centroids:
            counts[key] += 1
            centroids[key] += (vector - centroids[key]) / counts[key]
        else:
            centroids[key] = vector.copy()
            counts[key] = 1

    def new_key(face_id: int) -> str:
        return f"p{face_id}"

    for face_id, vector, key in zip(ids, matrix, keys):
        if key:
            continue
        best_key = None
        best_distance = threshold
        for person_key, centroid in centroids.items():
            distance = 1.0 - float(np.dot(vector, centroid))
            if distance <= best_distance:
                best_distance = distance
                best_key = person_key
        if best_key is None:
            best_key = new_key(face_id)
            centroids[best_key] = vector.copy()
            counts[best_key] = 1
        else:
            counts[best_key] += 1
            centroids[best_key] += (vector - centroids[best_key]) / counts[best_key]
        connection.execute(
            "UPDATE faces SET person_key = ? WHERE id = ?",
            (best_key, face_id),
        )
    grouped = connection.execute(
        """
        SELECT COUNT(*) FROM (
            SELECT person_key FROM faces
            WHERE person_key IS NOT NULL
            GROUP BY person_key
            HAVING COUNT(*) >= 2
        )
        """
    ).fetchone()[0]
    return int(grouped)


def list_people(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        """
        SELECT faces.person_key AS person_key,
               COUNT(*) AS face_count,
               COUNT(DISTINCT faces.file_id) AS photo_count,
               MIN(faces.file_id) AS sample_id,
               people.name AS name
        FROM faces
        LEFT JOIN people ON people.person_key = faces.person_key
        WHERE faces.person_key IS NOT NULL
        GROUP BY faces.person_key
        HAVING COUNT(*) >= 2
        ORDER BY photo_count DESC, faces.person_key
        """
    ).fetchall()
    return [
        {
            "person_key": row["person_key"],
            "name": row["name"] or "",
            "face_count": row["face_count"],
            "photo_count": row["photo_count"],
            "sample_id": row["sample_id"],
        }
        for row in rows
    ]


def name_person(connection: sqlite3.Connection, person_key: str, name: str) -> None:
    cleaned = name.strip()
    if not person_key or len(person_key) > 64 or not person_key.startswith("p"):
        raise ValueError("unknown person")
    exists = connection.execute(
        "SELECT 1 FROM faces WHERE person_key = ? LIMIT 1",
        (person_key,),
    ).fetchone()
    if exists is None:
        raise ValueError("unknown person")
    if cleaned:
        connection.execute(
            "INSERT INTO people(person_key, name) VALUES (?, ?) ON CONFLICT(person_key) DO UPDATE SET name = excluded.name",
            (person_key, cleaned[:80]),
        )
    else:
        connection.execute("DELETE FROM people WHERE person_key = ?", (person_key,))
