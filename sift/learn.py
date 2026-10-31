"""Suggest Keep or Noise from photos you already marked.

This is nearest-example distance on the 64-bit dhash, not a trained model.
A screenshot with no similar Keep is suggested as Noise.
"""

import sqlite3

MARGIN = 4


def _hashes(connection: sqlite3.Connection, label: str) -> list[int]:
    rows = connection.execute(
        "SELECT dhash FROM files WHERE label = ? AND dhash IS NOT NULL AND dhash != ''",
        (label,),
    )
    values = []
    for row in rows:
        try:
            values.append(int(row["dhash"], 16))
        except ValueError:
            continue
    return values


def _nearest(digest: int, examples: list[int]) -> int:
    if not examples:
        return 64
    return min((digest ^ other).bit_count() for other in examples)


def suggest(row: sqlite3.Row, keep_hashes: list[int], noise_hashes: list[int]) -> str | None:
    if row["label"] in ("keep", "noise"):
        return None
    raw = row["dhash"]
    if not raw:
        return "noise" if row["is_screenshot"] else None
    try:
        digest = int(raw, 16)
    except ValueError:
        return "noise" if row["is_screenshot"] else None
    distance_keep = _nearest(digest, keep_hashes)
    distance_noise = _nearest(digest, noise_hashes)
    if distance_keep == 64 and distance_noise == 64:
        return "noise" if row["is_screenshot"] else None
    if distance_noise + MARGIN < distance_keep:
        return "noise"
    if distance_keep + MARGIN < distance_noise:
        return "keep"
    if row["is_screenshot"] and distance_keep >= distance_noise:
        return "noise"
    return None


def load_examples(connection: sqlite3.Connection) -> tuple[list[int], list[int]]:
    return _hashes(connection, "keep"), _hashes(connection, "noise")
