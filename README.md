Download or sync a YouTube playlist to a local folder.

When run, new songs are downloaded, already downloaded songs are skipped, and songs that have been removed from the YouTube playlist are removed from the local folder.

The script was created with AI as it was not meant to be public.

## Requirements
1. Install [Python 3.10+](https://www.python.org/downloads/).
2. Download [yt-dlp](https://github.com/yt-dlp/yt-dlp).
3. Download [FFmpeg](https://ffmpeg.org/download.html)
	- Add FFmpeg to your system `PATH`.
4. Install [Deno](https://deno.com/) (OPTIONAL).
    - Either place `deno.exe` in the same directory as `yt-dlp.exe`, or add Deno to your system `PATH`.
5. Download `save_youtube_playlist.py` from this repository and place it in the same directory as `yt-dlp.exe`.

Your directory should look something like this:
```
yt_playlist_downloader/
- save_youtube_playlist.py
- yt-dlp.exe
- deno.exe
```

## Converting a Spotify Playlist
This script uses a YouTube playlist as the source for downloading.
1. Go to [TuneMyMusic](https://www.tunemymusic.com/).
2. Convert your Spotify playlist to YouTube Music.
3. Open the newly created YouTube playlist.
4. Change the playlist visibility from `Private` to `Unlisted` or `Public`.
5. Copy the YouTube playlist URL.

## Running the Script
Run `save_youtube_playlist.py` by double-clicking it, or run it from a terminal:
```bash
python save_youtube_playlist.py
```

The script will ask for the following:
1. Folder name
    - Enter the name of the folder where the music should be saved.
    - You can reuse an existing folder to update it, or enter a new name.
2. YouTube playlist URL
    - Paste the URL copied from the previous step.
3. Playlist confirmation
    - Confirm that the detected playlist is the correct playlist when prompted.
4. Download
    - The script will download the playlist and save the files to the selected folder.

## Limitations
### YouTube Rate Limiting
Downloading a large number of songs in a short period may trigger YouTube rate limiting. If this happens, you may need to wait before continuing.
### TuneMyMusic Accuracy
TuneMyMusic is not perfect. Some songs may fail to transfer from Spotify to YouTube, while others may transfer to an incorrect or different version of the song.