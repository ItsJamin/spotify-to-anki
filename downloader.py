import pathlib
import re
import subprocess
import sys

from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3


OUTPUT_DIR = pathlib.Path("songs")
SONG_FILENAME = "song.mp3"


def download_playlist(playlist_url: str):
    """Let spotDL downlod the whole playlist into per-track folders."""
    # {artists} and {title} are spotDL output-template variables
    template = str(OUTPUT_DIR / "{artists} - {title}" / "song.{output-ext}")
    cmd = ["spotdl", "download", playlist_url, "--output", template]
    print("Running spotDL ... (this can take a while)\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit("spotDL failed — check the errors above.")


def extract_metadata():
    """Write info.txt and cover.png next to each downloaded song.mp3."""
    processed = 0
    for song in OUTPUT_DIR.glob("*/" + SONG_FILENAME):
        folder = song.parent

        # --- info.txt (title on line 1, artist on line 2) ---
        try:
            tags = EasyID3(str(song))
            title = str(tags.get("title", [song.stem])[0])
            artist = str(tags.get("artist", ["Unknown Artist"])[0])
        except Exception:
            title, artist = song.stem, "Unknown Artist"

        (folder / "info.txt").write_text(f"{title}\n{artist}\n", encoding="utf-8")

        # --- cover.png from the embedded artwork ---
        cover = folder / "cover.png"
        if not cover.exists():
            try:
                id3 = ID3(str(song))
                for key in id3.keys():
                    if key.startswith("APIC:"):
                        cover.write_bytes(id3[key].data)
                        break
            except Exception as e:
                print(f"  no cover found for {folder.name}: {e}")

        print(f"  ok: {folder.name}")
        processed += 1

    return processed


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python downloader.py <spotify-playlist-url>')

    url = sys.argv[1]
    if "playlist" not in url and not re.fullmatch(r"[A-Za-z0-9]+", url):
        sys.exit("Only Spotify playlist link/ID.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    download_playlist(url)

    print("\nWriting info.txt and extracting covers ...")
    count = extract_metadata()
    print(f"\nDone — {count} songs saved to '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    main()
