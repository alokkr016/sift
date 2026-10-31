# Sift

Sift indexes photos that are already on this Mac and lets you mark each one **Keep** or **Noise**. Scanning only reads files. A photo moves or goes to the Finder Trash only when you confirm that action in the review window. There is no permanent delete, and nothing is uploaded.

This version is local folders only. Phone libraries, Google Drive, and sentence search are not in yet.

## Install

Needs Python 3.11 or newer. On this Mac, `python3` is 3.9, so use Homebrew `python3.13`.

```bash
cd ~/Documents/sift
python3.13 -m venv .venv
.venv/bin/pip install -e .
```

The `sift` command is then `.venv/bin/sift`. Every command accepts `--db` when the index should not live in the default place.

## Commands

```bash
.venv/bin/sift scan ~/Pictures/some-folder
.venv/bin/sift stats
.venv/bin/sift faces
.venv/bin/sift app
.venv/bin/sift serve
```

| Command | What it does |
| --- | --- |
| `scan <folder>` | Index JPEG, PNG, WebP, GIF, and TIFF files under that folder. Prints seen, added, updated, unchanged, unreadable, and duplicate-group counts. |
| `stats` | Print photo, label, screenshot, duplicate-group, face, and people counts, plus the index path. |
| `faces` | Find faces with Apple's Vision framework and group similar face crops. Only reads files already in the index. Slow on a few thousand photos. |
| `app` | Open the desktop window. Default port is 8765. |
| `serve` | Leave the same page in the browser at http://127.0.0.1:8765. |

A second scan skips a file when its path, size, and modification time are unchanged. Keep and Noise marks stay.

## Review

`sift app` and `sift serve` show only files indexed under a folder you scanned.

- `K` marks Keep. `N` marks Noise. `S` skips. Left and right arrows move between photos.
- With no marks yet, screenshots are suggested as Noise. After that, suggestions come from the hashes of photos you have already marked. A suggestion is a hint until you press Keep or Noise.
- **Trash** and **Move** ask first. Move needs a full folder path. Near-duplicates can send the other copies to the Trash while the photo on screen stays.
- You can name a face group. Face data stays in the local index.

A file counts as a screenshot when the name contains `Screenshot` or `Screen Shot`, or when it is a PNG with no camera Make or Model, no DateTimeOriginal, and a long-side/short-side ratio between 1.7 and 2.4.

## Index

The default index is `~/Library/Application Support/Sift/sift.sqlite`, mode `0600`. It stores path, size, time, pixel size, and a 64-bit difference hash.

Near-duplicates are photos whose hashes differ by at most 8 bits. Under about 8,000 hashed photos, grouping compares every pair. Above that it uses hash bands and can miss some near-duplicates.

## Limits

- HEIC is not read. Pillow cannot open it without an extra plugin.
- There is no trained classifier. Suggestions stay nearest-hash hints.
- Scan itself does not delete, trash, or move originals.

## Tests

```bash
.venv/bin/python -m unittest discover -s tests
```

## Libraries

Perceptual hashing uses [imagehash](https://github.com/JohannesBuchner/imagehash) (BSD) and Pillow. The ideas for culling and duplicates are informed by local tools such as Lap and picurate. Those projects are GPL-3, so this app does not copy their code.

## Contributing

Contributions are welcome. Open a pull request against `main`. Run the tests before you send it. Your changes are accepted under the MIT License.

## License

Sift is released under the [MIT License](LICENSE). You can use, change, and share it, including in your own projects.
