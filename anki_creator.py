import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import genanki


MODEL_ID = 1607392319001   # keep fixed so re-imports update the same cards
DECK_ID = 1607392319002
DECK_NAME = "Songs"

CARD_CSS = """
.card {
  font-family: -apple-system, 'Segoe UI', Roboto, Arial, sans-serif;
  text-align: center; background: #fff; color: #222;
  padding: 16px;
}
.cover {
  max-width: 100px; width: 25%;
  border-radius: 10px;
  box-shadow: 0 4px 14px rgba(0,0,0,.15);
}
.title  { font-size: 26px; font-weight: 700; margin-top: 14px; }
.artist { font-size: 20px; color: #555; margin-top: 4px; }
.answer { border: none; margin: 18px 0 8px; }

/* modern audio player styling (browsers that support it) */
audio {
  width: 320px; max-width: 100%;
  height: 44px; border-radius: 22px;
  outline: none;
}
audio::-webkit-media-controls-enclosure {
  border-radius: 22px;
  box-shadow: 0 2px 10px rgba(0,0,0,.15);
}
.player-wrap { margin: 24px auto 0; }
"""

class SongModel(genanki.Model):
    def __init__(self):
        super().__init__(
            model_id=MODEL_ID,
            name="Song Model",
            fields=[
                {"name": "Audio"},
                {"name": "Cover"},
                {"name": "Title"},
                {"name": "Artist"},
            ],
            templates=[
                {
                    "name": "Guess the song",
                    "qfmt": """
<div class="player-wrap">{{Audio}}</div>
""",
                    "afmt": """
{{Cover}}
<div class="title">{{Title}}</div>
<div class="artist">{{Artist}}</div>
<hr class="answer">
{{Audio}}
""",
                },
            ],
            css=CARD_CSS,
        )


def sanitize(name: str) -> str:
    """Make a string safe to use as an Anki media filename."""
    name = name.replace('"', "").replace("'", "")
    name = re.sub(r"[\\/*?<>:|&;#%{}^~`$]", "", name)   # src/html-breaking chars
    name = re.sub(r"\s+", " ", name).strip()
    return name or "unknown"


def make_clip(song: pathlib.Path, dest: pathlib.Path, seconds: int) -> bool:
    """Cut the first N seconds with ffmpeg. Returns False if it fails."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(song), "-t", str(seconds),
         "-vn", "-c:a", "libmp3lame", "-q:a", "4", str(dest)],
        capture_output=True,
    )
    return result.returncode == 0 and dest.is_file() and dest.stat().st_size > 0


def build_deck(songs_dir: pathlib.Path, media_dir: pathlib.Path, seconds: int):
    """Create notes and copy media files to media_dir under unique names."""
    model = SongModel()
    deck = genanki.Deck(deck_id=DECK_ID, name=DECK_NAME)

    skipped = []
    used_names = set()
    count = 0

    for folder in sorted(songs_dir.iterdir()):
        if not folder.is_dir():
            continue

        song = folder / "song.mp3"
        if not song.is_file() or song.stat().st_size == 0:
            skipped.append(folder.name)  # empty/missing song -> skip
            continue

        # --- read info.txt if present (line 1: title, line 2: artist) ---
        info = folder / "info.txt"
        title, artist = folder.name, "Unknown Artist"
        if info.is_file():
            lines = info.read_text(encoding="utf-8").strip().splitlines()
            if len(lines) >= 1 and lines[0]:
                title = lines[0]
            if len(lines) >= 2 and lines[1]:
                artist = lines[1]

        # --- unique, sanitized media basenames ---
        base = sanitize(folder.name)
        while base in used_names:
            base += "_"
        used_names.add(base)

        audio_name = f"{base}.mp3"
        cover_name = f"{base}.png"

        # cut the first N seconds; fall back to the full song
        if not make_clip(song, media_dir / audio_name, seconds):
            shutil.copy2(song, media_dir / audio_name)
            print(f"  (ffmpeg unavailable/failed — using full song: {folder.name})")

        cover_src = folder / "cover.png"
        has_cover = cover_src.is_file()
        if has_cover:
            shutil.copy2(cover_src, media_dir / cover_name)

        audio_field = f"[sound:{audio_name}]"
        if has_cover:
            cover_field = f'<img class="cover" src="{cover_name}">'
        else:
            cover_field = ""

        note = genanki.Note(
            model=model,
            fields=[audio_field, cover_field, title, artist],
            guid=genanki.guid_for(folder.name),
        )
        deck.add_note(note)
        count += 1

    return deck, skipped, count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="songs", help="folder containing the song folders")
    ap.add_argument("--out", default="songs.apkg", help="output .apkg file")
    ap.add_argument("--seconds", type=int, default=30,
                    help="length of the included song clip (default: 30)")
    args = ap.parse_args()

    songs_dir = pathlib.Path(args.dir)
    if not songs_dir.is_dir():
        sys.exit(f"Folder not found: {songs_dir}")

    # temp dir for uniquely-named copies of the media files
    media_dir = pathlib.Path(tempfile.mkdtemp(prefix="anki_media_"))
    try:
        deck, skipped, count = build_deck(songs_dir, media_dir, args.seconds)
        if count == 0:
            sys.exit("No valid songs found — nothing to do.")

        package = genanki.Package(deck, media_files=[
            str(p) for p in sorted(media_dir.iterdir())
        ])
        package.write_to_file(args.out)
    finally:
        shutil.rmtree(media_dir, ignore_errors=True)

    print(f"Done: {count} cards ({args.seconds}s clips) -> {args.out}")
    if skipped:
        print(f"Skipped {len(skipped)} empty folder(s):")
        for name in skipped:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
