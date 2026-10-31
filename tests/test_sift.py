import io
import json
import random
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from PIL import Image

from sift.db import connect
from sift.duplicates import hamming, rebuild_groups
from sift.learn import load_examples, suggest
from sift.review import allowed_file, make_handler
from sift.scan import looks_like_screenshot, scan_folder
from http.server import ThreadingHTTPServer


def _pattern(seed: int, size: int = 64) -> Image.Image:
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    generator = random.Random(seed)
    for y in range(size):
        for x in range(size):
            pixels[x, y] = (
                generator.randrange(256),
                generator.randrange(256),
                generator.randrange(256),
            )
    return image


class ScreenshotTests(unittest.TestCase):
    def test_filename_counts_even_when_the_picture_is_square(self):
        self.assertTrue(looks_like_screenshot(Path("Screenshot 1.png"), 100, 100, False, False))
        self.assertTrue(looks_like_screenshot(Path("Screen Shot 2024.png"), 100, 100, True, True))

    def test_phone_png_without_camera_exif_counts(self):
        self.assertTrue(looks_like_screenshot(Path("IMG.png"), 1170, 2532, False, False))

    def test_camera_jpeg_and_odd_aspect_do_not(self):
        self.assertFalse(looks_like_screenshot(Path("IMG.png"), 1170, 2532, True, False))
        self.assertFalse(looks_like_screenshot(Path("IMG.png"), 1170, 2532, False, True))
        self.assertFalse(looks_like_screenshot(Path("note.png"), 100, 100, False, False))
        self.assertFalse(looks_like_screenshot(Path("classic.png"), 400, 300, False, False))
        self.assertFalse(looks_like_screenshot(Path("phone.jpg"), 1170, 2532, False, False))

    def test_aspect_edges(self):
        self.assertTrue(looks_like_screenshot(Path("a.png"), 1700, 1000, False, False))
        self.assertTrue(looks_like_screenshot(Path("a.png"), 2400, 1000, False, False))
        self.assertFalse(looks_like_screenshot(Path("a.png"), 1699, 1000, False, False))
        self.assertFalse(looks_like_screenshot(Path("a.png"), 2401, 1000, False, False))


class ScanTests(unittest.TestCase):
    def test_scan_labels_screenshot_camera_and_duplicates(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            _pattern(1).save(folder / "a.png")
            _pattern(1).save(folder / "a-copy.png")
            _pattern(2).save(folder / "other.png")
            shot = Image.new("RGB", (1170, 2532), (20, 20, 20))
            shot.save(folder / "notes.png")
            camera = _pattern(3)
            exif = Image.Exif()
            exif[271] = "TestCam"
            camera.save(folder / "camera.jpg", exif=exif)
            db_path = folder / "index.sqlite"
            first = scan_folder(folder, db_path)
            self.assertEqual(first["added"], 5)
            self.assertGreaterEqual(first["duplicate_groups"], 1)
            second = scan_folder(folder, db_path)
            self.assertEqual(second["added"], 0)
            self.assertEqual(second["unchanged"], 5)

            connection = connect(db_path)
            try:
                screenshots = connection.execute(
                    "SELECT path FROM files WHERE is_screenshot = 1"
                ).fetchall()
                self.assertEqual(len(screenshots), 1)
                self.assertTrue(screenshots[0]["path"].endswith("notes.png"))
                camera_row = connection.execute(
                    "SELECT has_camera, is_screenshot FROM files WHERE path LIKE '%camera.jpg'"
                ).fetchone()
                self.assertEqual(camera_row["has_camera"], 1)
                self.assertEqual(camera_row["is_screenshot"], 0)
                groups = connection.execute(
                    """
                    SELECT COUNT(*) FROM dup_groups
                    WHERE group_key IN (
                      SELECT group_key FROM dup_groups GROUP BY group_key HAVING COUNT(*) = 2
                    )
                    """
                ).fetchone()[0]
                self.assertEqual(groups, 2)
            finally:
                connection.close()

    def test_symlink_is_not_indexed(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / "library"
            outside = Path(raw) / "outside"
            folder.mkdir()
            outside.mkdir()
            image = outside / "secret.png"
            _pattern(9).save(image)
            (folder / "link.png").symlink_to(image)
            summary = scan_folder(folder, Path(raw) / "index.sqlite")
            self.assertEqual(summary["seen"], 0)


class LearnTests(unittest.TestCase):
    def test_nearest_label_wins_and_user_marks_are_left_alone(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            keep = _pattern(4)
            noise = _pattern(5)
            keep.save(folder / "keep.png")
            noise.save(folder / "noise.png")
            similar = keep.copy()
            similar.putpixel((0, 0), (1, 2, 3))
            similar.save(folder / "similar.png")
            db_path = folder / "index.sqlite"
            scan_folder(folder, db_path)
            connection = connect(db_path)
            try:
                connection.execute("UPDATE files SET label = 'keep' WHERE path LIKE '%/keep.png'")
                connection.execute("UPDATE files SET label = 'noise' WHERE path LIKE '%/noise.png'")
                connection.commit()
                keep_hashes, noise_hashes = load_examples(connection)
                row = connection.execute("SELECT * FROM files WHERE path LIKE '%/similar.png'").fetchone()
                self.assertEqual(suggest(row, keep_hashes, noise_hashes), "keep")
                marked = connection.execute("SELECT * FROM files WHERE path LIKE '%/keep.png'").fetchone()
                self.assertIsNone(suggest(marked, keep_hashes, noise_hashes))
            finally:
                connection.close()


class DuplicateTests(unittest.TestCase):
    def test_hamming(self):
        self.assertEqual(hamming(0b1111, 0b1100), 2)


class ReviewTests(unittest.TestCase):
    def test_media_stays_inside_scanned_roots_and_labels_stick(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / "photos"
            folder.mkdir()
            _pattern(7).save(folder / "one.png")
            outside = Path(raw) / "outside.png"
            _pattern(8).save(outside)
            db_path = Path(raw) / "index.sqlite"
            scan_folder(folder, db_path)
            connection = connect(db_path)
            try:
                file_id = connection.execute("SELECT id FROM files").fetchone()["id"]
                self.assertIsNotNone(allowed_file(connection, file_id))
                connection.execute(
                    "INSERT INTO files(path, size, mtime, scanned_at) VALUES (?, 1, 1, 1)",
                    (str(outside.resolve()),),
                )
                connection.commit()
                outside_id = connection.execute(
                    "SELECT id FROM files WHERE path = ?",
                    (str(outside.resolve()),),
                ).fetchone()["id"]
                self.assertIsNone(allowed_file(connection, outside_id))
            finally:
                connection.close()

            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db_path))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_address[1]
            try:
                base = f"http://127.0.0.1:{port}"
                with urllib.request.urlopen(base + "/api/next?bucket=inbox") as response:
                    item = json.load(response)
                self.assertEqual(item["name"], "one.png")
                body = json.dumps({"id": item["id"], "label": "noise"}).encode()
                request = urllib.request.Request(
                    base + "/api/label",
                    data=body,
                    headers={"Content-Type": "application/json", "X-Sift": "1"},
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(json.load(response)["label"], "noise")
                denied = urllib.request.Request(
                    base + "/api/label",
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    urllib.request.urlopen(denied)
                self.assertEqual(caught.exception.code, 400)
                with urllib.request.urlopen(base + f"/media/{item['id']}") as response:
                    self.assertEqual(response.headers.get("Content-Type"), "image/jpeg")
                    Image.open(io.BytesIO(response.read()))
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + f"/media/{outside_id}")
            finally:
                server.shutdown()
                server.server_close()

    def test_rebuild_groups_on_a_fresh_connection(self):
        with tempfile.TemporaryDirectory() as raw:
            db_path = Path(raw) / "index.sqlite"
            connection = connect(db_path)
            try:
                self.assertEqual(rebuild_groups(connection), 0)
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
