"""Group near-duplicate photos by dhash Hamming distance."""

import sqlite3
from collections import defaultdict

# 64-bit dhash. 8 bits is a tight near-duplicate band (same shot, light edit).
HAMMING_THRESHOLD = 8
# Full pairwise compare stays correct and is fine for a personal library.
PAIRWISE_LIMIT = 8000


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def rebuild_groups(connection: sqlite3.Connection, threshold: int = HAMMING_THRESHOLD) -> int:
    rows = connection.execute(
        "SELECT id, dhash FROM files WHERE dhash IS NOT NULL AND dhash != ''"
    ).fetchall()
    items: list[tuple[int, int]] = []
    for row in rows:
        try:
            items.append((row["id"], int(row["dhash"], 16)))
        except ValueError:
            continue

    parent = {file_id: file_id for file_id, _ in items}

    def find(file_id: int) -> int:
        while parent[file_id] != file_id:
            parent[file_id] = parent[parent[file_id]]
            file_id = parent[file_id]
        return file_id

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    if len(items) > PAIRWISE_LIMIT:
        _union_banded(items, union, threshold)
    else:
        for index, (left_id, left_hash) in enumerate(items):
            for right_id, right_hash in items[index + 1 :]:
                if hamming(left_hash, right_hash) <= threshold:
                    union(left_id, right_id)

    clusters: dict[int, list[int]] = defaultdict(list)
    for file_id, _ in items:
        clusters[find(file_id)].append(file_id)

    connection.execute("DELETE FROM dup_groups")
    group_count = 0
    for members in clusters.values():
        if len(members) < 2:
            continue
        group_count += 1
        group_key = str(min(members))
        for file_id in members:
            connection.execute(
                "INSERT INTO dup_groups(file_id, group_key) VALUES (?, ?)",
                (file_id, group_key),
            )
    return group_count


def _union_banded(items: list[tuple[int, int]], union, threshold: int) -> None:
    """Compare hashes that share a 16-bit band. Misses some pairs past ~8k files."""
    bands = (48, 32, 16, 0)
    for shift in bands:
        buckets: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for file_id, digest in items:
            buckets[(digest >> shift) & 0xFFFF].append((file_id, digest))
        for bucket in buckets.values():
            if len(bucket) < 2 or len(bucket) > 400:
                continue
            for index, (left_id, left_hash) in enumerate(bucket):
                for right_id, right_hash in bucket[index + 1 :]:
                    if hamming(left_hash, right_hash) <= threshold:
                        union(left_id, right_id)
