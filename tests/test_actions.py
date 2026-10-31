import random
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from sift.actions import ActionError, move_indexed
from sift.db import connect
from sift.faces import assign_people, crop_box
from sift.review import duplicate_group, person_photos
from sift.scan import scan_folder


def _pattern(seed: int) -> Image.Image:
    image = Image.new("RGB", (64, 64))
    pixels = image.load()
    generator = random.Random(seed)
    for y in range(64):
        for x in range(64):
            pixels[x, y] = (generator.randrange(256), generator.randrange(256), generator.randrange(256))
    return image


class CropTests(unittest.TestCase):
    def test_vision_box_uses_a_bottom_left_origin(self):
        # A box covering the top half of a 100x100 image.
        self.assertEqual(crop_box(100, 100, 0.0, 0.5, 1.0, 0.5, pad=0), (0, 0, 100, 50))


class MoveTests(unittest.TestCase):
    def test_move_updates_the_index_and_leaves_the_bytes_in_place_until_asked(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "photos"
            dest = root / "kept"
            source.mkdir()
            dest.mkdir()
            Image.new("RGB", (32, 32), (10, 20, 30)).save(source / "one.png")
            db_path = root / "index.sqlite"
            scan_folder(source, db_path)
            connection = connect(db_path)
            try:
                file_id = connection.execute("SELECT id FROM files").fetchone()["id"]
                moved = move_indexed(connection, file_id, dest)
                connection.commit()
                self.assertFalse((source / "one.png").exists())
                self.assertTrue(Path(moved).is_file())
                self.assertTrue(moved.endswith("/kept/one.png"))
                with self.assertRaises(ActionError):
                    move_indexed(connection, file_id, root / "missing")
            finally:
                connection.close()


class DuplicateViewTests(unittest.TestCase):
    def test_a_group_includes_every_copy(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            image = _pattern(1)
            image.save(folder / "a.png")
            image.save(folder / "b.png")
            _pattern(2).save(folder / "solo.png")
            db_path = folder / "index.sqlite"
            scan_folder(folder, db_path)
            connection = connect(db_path)
            try:
                group = duplicate_group(connection, set())
                self.assertIsNotNone(group)
                names = {item["name"] for item in group["files"]}
                self.assertEqual(names, {"a.png", "b.png"})
                self.assertEqual(len(group["files"]), 2)
            finally:
                connection.close()


class PeopleTests(unittest.TestCase):
    def test_similar_face_vectors_share_a_person(self):
        with tempfile.TemporaryDirectory() as raw:
            db_path = Path(raw) / "index.sqlite"
            connection = connect(db_path)
            try:
                for index in (1, 2, 3):
                    connection.execute(
                        "INSERT INTO files(path, size, mtime, scanned_at) VALUES (?, 1, 1, 1)",
                        (str(Path(raw) / f"{index}.png"),),
                    )
                same = np.ones(16, dtype=np.float32)
                same /= np.linalg.norm(same)
                other = np.zeros(16, dtype=np.float32)
                other[0] = 1
                blobs = [same.tobytes(), same.tobytes(), other.tobytes()]
                for index, blob in enumerate(blobs, start=1):
                    connection.execute(
                        "INSERT INTO faces(file_id, x, y, w, h, feature) VALUES (?, 0, 0, 1, 1, ?)",
                        (index, blob),
                    )
                groups = assign_people(connection, threshold=0.2)
                self.assertEqual(groups, 1)
                keys = [row[0] for row in connection.execute("SELECT person_key FROM faces ORDER BY id")]
                self.assertEqual(keys[0], keys[1])
                self.assertNotEqual(keys[0], keys[2])
                photos = person_photos(connection, keys[0])
                self.assertEqual(len(photos["files"]), 2)
                self.assertEqual(
                    {item["name"] for item in photos["files"]},
                    {"1.png", "2.png"},
                )
            finally:
                connection.close()
