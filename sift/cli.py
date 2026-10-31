import argparse
import sys
from pathlib import Path

from sift.db import connect, default_db
from sift.faces import scan_faces
from sift.review import serve
from sift.scan import scan_folder


def _db(value: str | None) -> Path:
    return Path(value).expanduser() if value else default_db()


def _print_stats(db_path: Path) -> None:
    connection = connect(db_path)
    try:
        total = connection.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        unlabeled = connection.execute("SELECT COUNT(*) FROM files WHERE label IS NULL").fetchone()[0]
        screenshots = connection.execute("SELECT COUNT(*) FROM files WHERE is_screenshot = 1").fetchone()[0]
        keep = connection.execute("SELECT COUNT(*) FROM files WHERE label = 'keep'").fetchone()[0]
        noise = connection.execute("SELECT COUNT(*) FROM files WHERE label = 'noise'").fetchone()[0]
        groups = connection.execute("SELECT COUNT(DISTINCT group_key) FROM dup_groups").fetchone()[0]
        faces = connection.execute("SELECT COUNT(*) FROM faces").fetchone()[0]
        people = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT person_key FROM faces
                WHERE person_key IS NOT NULL
                GROUP BY person_key HAVING COUNT(*) >= 2
            )
            """
        ).fetchone()[0]
    finally:
        connection.close()
    print(f"photos        {total}")
    print(f"unlabeled     {unlabeled}")
    print(f"screenshots   {screenshots}")
    print(f"keep          {keep}")
    print(f"noise         {noise}")
    print(f"dup groups    {groups}")
    print(f"faces         {faces}")
    print(f"people        {people}")
    print(f"index         {db_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sift", description="Index local photos and mark Keep or Noise.")
    parser.add_argument("--db", help="SQLite index path. Default is ~/Library/Application Support/Sift/sift.sqlite")
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="Index images under a folder. Nothing is moved or deleted.")
    scan.add_argument("folder", type=Path)

    commands.add_parser("stats", help="Show index counts.")

    review = commands.add_parser("serve", help="Open the review page in a browser.")
    review.add_argument("--port", type=int, default=8765)

    app = commands.add_parser("app", help="Open the Sift desktop window.")
    app.add_argument("--port", type=int, default=8765)

    commands.add_parser("faces", help="Find faces on this Mac and group similar ones.")

    args = parser.parse_args(argv)
    db_path = _db(args.db)
    try:
        if args.command == "scan":
            summary = scan_folder(args.folder, db_path)
            print(
                f"seen {summary['seen']}, added {summary['added']}, "
                f"updated {summary['updated']}, unchanged {summary['unchanged']}, "
                f"unreadable {summary['unreadable']}, duplicate groups {summary['duplicate_groups']}"
            )
            print(f"index {db_path}")
            return 0
        if args.command == "stats":
            _print_stats(db_path)
            return 0
        if args.command == "serve":
            serve(db_path, args.port)
            return 0
        if args.command == "app":
            from sift.desktop import open_window

            open_window(db_path, args.port)
            return 0
        if args.command == "faces":
            summary = scan_faces(db_path)
            print(
                f"checked {summary['photos']}, faces {summary['faces']}, "
                f"unreadable {summary['failed']}, people groups {summary['people']}"
            )
            return 0
    except NotADirectoryError as exc:
        print(f"not a folder: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
