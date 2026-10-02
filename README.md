# Make Anki Cards out of songs

### Usage

```
python spotify_downloader.py <spotify_playlist_url>
python anki_creator.py --seconds <length_of_audio>
```

### Spotify Playlist Downloader

Downloads every track of a Spotify playlist into:
```
songs/
    <Artist - Title>/
    song.mp3
    cover.png
    info.txt        (line 1: title, line 2: artist)
```
Folder is empty if failed. 

### Anki Creator

Creates a `.apkg` file out of the songs.