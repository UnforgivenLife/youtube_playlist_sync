import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')
VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')
TRAILING_ID = re.compile(r'\[([A-Za-z0-9_-]{11})\]$')
MUSIC_YOUTUBE_HOST = re.compile(r'^(https?://)(?:music\.)youtube\.com', re.IGNORECASE)


def pause_and_exit(code):
    input("Press Enter to exit")
    sys.exit(code)


def get_safe_folder_name(name):
    name = INVALID_CHARS.sub('_', name).strip()
    if not name:
        raise ValueError("Folder name cannot be empty.")
    return name


def normalize_youtube_url(url: str) -> str:
    return MUSIC_YOUTUBE_HOST.sub(r'\1www.youtube.com', url.strip())


def new_unique_destination_path(folder: Path, file_name: str) -> Path:
    candidate = folder / file_name
    if not candidate.exists():
        return candidate

    base = Path(file_name).stem
    ext = Path(file_name).suffix
    i = 1
    while True:
        candidate = folder / f"{base} ({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1


def move_file_safely(source_path: Path, destination_folder: Path) -> Path:
    destination_folder.mkdir(parents=True, exist_ok=True)
    dest_path = new_unique_destination_path(destination_folder, source_path.name)
    try:
        os.chmod(source_path, 0o666)
    except OSError:
        pass
    shutil.move(str(source_path), str(dest_path))
    return dest_path


def run_capture(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return (result.stdout or "") + (result.stderr or "")


def main():
    folder_name = get_safe_folder_name(input("Enter folder name to save into: "))
    raw_url = input("Enter YouTube playlist URL: ").strip()

    if not raw_url:
        print("ERROR: No playlist URL provided.")
        pause_and_exit(1)

    url = normalize_youtube_url(raw_url)

    script_dir = Path(__file__).resolve().parent
    folder = script_dir / "DownloadedFromCloud" / "LocalYouTube" / folder_name
    backups = folder / "backups"

    local_deno = script_dir / "deno.exe"
    env_deno = os.environ.get("DENO_PATH")

    if local_deno.exists():
        deno = str(local_deno)
    elif env_deno and Path(env_deno).is_file():
        deno = env_deno
    elif env_deno and (Path(env_deno) / "deno.exe").is_file():
        deno = str(Path(env_deno) / "deno.exe")
    else:
        deno = shutil.which("deno")

    ytdlp = script_dir / "yt-dlp.exe"

    if deno is None:
        raise FileNotFoundError(
            "deno.exe not found next to the script, in the DENO_PATH "
            "environment variable, or on PATH."
        )

    if not ytdlp.exists():
        raise FileNotFoundError(f"yt-dlp.exe not found at {ytdlp}")

    try:
        rel_folder = os.path.relpath(folder, Path.cwd())
    except ValueError:
        rel_folder = str(folder)
    print(f"Saving to: {rel_folder}")
    folder.mkdir(parents=True, exist_ok=True)

    if backups.exists():
        shutil.rmtree(backups, ignore_errors=True)
    backups.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------
    # Step 1 - Fetch playlist IDs (+ title, for the sanity check below)
    # -------------------------------------------------------
    print("\n[1/3] Fetching playlist info from YouTube...")

    output = run_capture([
        str(ytdlp), "--flat-playlist", "--ignore-errors", "--no-warnings",
        "--print", "%(playlist_title)s\t%(id)s", url, "--js-runtimes", f"deno:{deno}"
    ])

    playlist_ids = []
    playlist_title = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        title_part, _, id_part = line.partition("\t")
        id_part = id_part.strip()
        if VIDEO_ID.match(id_part):
            playlist_ids.append(id_part)
            if playlist_title is None and title_part.strip():
                playlist_title = title_part.strip()

    if not playlist_ids:
        print("ERROR: Could not fetch playlist, or playlist returned 0 items.")
        pause_and_exit(1)

    fetched_count = len(playlist_ids)
    print(f"  Playlist: {fetched_count} song(s)")

    # Sanity check: make sure the playlist we just fetched is actually the
    # one the user meant to put in this folder.
    print(f"\n  Playlist title on YouTube: {playlist_title or '(unknown - could not read title)'}")
    print(f"  Saving into folder:        {folder_name}")
    while True:
        confirm = input("  Does that look like the right playlist for this folder? (y/n): ").strip().lower()
        if confirm in ("y", "yes"):
            break
        elif confirm in ("n", "no"):
            print("Aborted. No files were changed.")
            pause_and_exit(1)
        else:
            print("  Please answer y/yes or n/no.")

    local_files = list(folder.glob("*.mp3"))
    local_count = len(local_files)
    print(f"  Local:    {local_count} song(s)")

    # -------------------------------------------------------
    # Step 2 - Build archive from existing files, then download
    # -------------------------------------------------------
    print("\n[2/3] Downloading new songs...")

    archive_file = script_dir / "downloaded.txt"
    try:
        if archive_file.exists():
            archive_file.unlink()

        seen_archive_ids = set()
        with open(archive_file, "a", encoding="utf-8") as f:
            for file in folder.glob("*.mp3"):
                match = TRAILING_ID.search(file.stem)
                if match:
                    vid = match.group(1)
                    if vid not in seen_archive_ids:
                        seen_archive_ids.add(vid)
                        f.write(f"youtube {vid}\n")

        subprocess.run([
            str(ytdlp), "-x", "--audio-format", "mp3", "--yes-playlist", "--no-mtime",
            "--ignore-errors", "--no-warnings",
            "--download-archive", str(archive_file),
            "-o", str(folder / "%(title)s [%(id)s].%(ext)s"),
            url, "--js-runtimes", f"deno:{deno}"
        ])
    finally:
        if archive_file.exists():
            archive_file.unlink()

    # -------------------------------------------------------
    # Step 3 - Move removed songs into backups + remove duplicates
    # -------------------------------------------------------
    print("\n[3/3] Checking for removed songs...")

    playlist_id_set = set(playlist_ids)
    flagged = removed = failed = skipped = 0
    seen_ids = set()

    for file in folder.glob("*.mp3"):
        match = TRAILING_ID.search(file.stem)
        if match:
            file_id = match.group(1)
            should_remove = False
            reason = ""

            if file_id not in playlist_id_set:
                should_remove = True
                reason = "not in playlist"
            elif file_id in seen_ids:
                should_remove = True
                reason = "duplicate"
            else:
                seen_ids.add(file_id)

            if should_remove:
                flagged += 1
                print(f"  Flagged ({reason}): {file.name}")
                try:
                    dest = move_file_safely(file, backups)
                    print(f"  Moved to backups: {dest.name}")
                    removed += 1
                except Exception as e:
                    failed += 1
                    print(f"  FAILED: {e}")
        else:
            print(f"  Skipping (no ID in filename): {file.name}")
            skipped += 1

    print()
    if flagged == 0:
        print("No songs flagged. Folder is in sync.")
    else:
        print(f"Flagged {flagged} song(s). Moved {removed} to backups.")
        if failed > 0:
            print(f"FAILED on {failed} file(s). Fix those before trusting the folder.")

    if skipped > 0:
        print(f"Skipped {skipped} file(s) with no ID in their name. They were left untouched.")

    final_count = len(list(folder.glob("*.mp3")))
    print(f"Final mp3 count: {final_count}")

    if final_count != fetched_count:
        print("WARNING: Folder count does not match playlist count.")
        print("That means there are still files without IDs, duplicates, or something else that needs checking.")

    if failed > 0:
        pause_and_exit(1)

    print("\nAll done!")
    pause_and_exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        pause_and_exit(1)
