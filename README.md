# Sift

Sift indexes photos that are already on this Mac and lets you mark each one **Keep** or **Noise**. The files stay where they are. Nothing is deleted or moved.

Version 0.1 is local folders only. Phone libraries, Google Drive, and sentence search come later.

## What it does

- Walks a folder of JPEG, PNG, WebP, GIF, and TIFF images.
- Stores path, size, time, pixel size, and a 64-bit difference hash in SQLite.
- Marks a file as a screenshot when the name contains `Screenshot` or `Screen Shot`, or when it is a PNG with no camera Make/Model, no DateTimeOriginal, and a long-side/short-side ratio between 1.7 and 2.4.
- Groups near-duplicates whose hashes differ by at most 8 bits.
- Suggests Keep or Noise from the hashes of photos you have already marked. With no marks yet, screenshots are suggested as Noise. A suggestion is only a hint until you press Keep or Noise.
- Opens a desktop window. The same page is also on `127.0.0.1`. It can only show files that were indexed under a folder you scanned.
- Moves a photo to a folder you pick, or to the Finder Trash, after you confirm. There is no permanent delete.
- Finds faces with Apple's Vision framework on this Mac and groups similar face crops. You can name a group. The face data stays in the local index.

## What it does not do

- It does not delete, trash, or move originals.
- It does not read HEIC yet (Pillow cannot open it without an extra plugin).
- It does not train a real classifier. That waits until a few hundred Keep/Noise marks exist.
- It does not upload anything.

## Run

Needs Python 3.11 or newer. On this Mac, `python3` is 3.9, so use Homebrew `python3.13`.

```bash
cd ~/Documents/sift
python3.13 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/sift scan ~/Pictures/some-folder
.venv/bin/sift faces
.venv/bin/sift app
```

`sift app` opens the window. `sift serve` leaves it in the browser at http://127.0.0.1:8765. Keys: `K` keep, `N` noise, `S` skip. Trash and Move ask first.

`sift faces` can take a while on a few thousand photos. It only reads files already in the index.

The index lives at `~/Library/Application Support/Sift/sift.sqlite` (mode 0600). Pass `--db` to put it somewhere else.

A second scan skips a file when its path, size, and modification time are unchanged. Your Keep/Noise marks stay.

## Libraries

Perceptual hashing uses [imagehash](https://github.com/JohannesBuchner/imagehash) (BSD) and Pillow. The ideas for culling and duplicates are informed by local tools such as Lap and picurate. Those projects are GPL-3, so this app does not copy their code. A later version can add SigLIP 2 embeddings for “find photos like this” search.

Duplicate grouping compares every pair while the library is under about 8,000 hashed photos. Above that it uses hash bands and can miss some near-duplicates.
