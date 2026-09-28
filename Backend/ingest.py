from pathlib import Path
from yt_dlp import YoutubeDL

VIDEOS_DIR = Path("../videos")
VIDEOS_DIR.mkdir(exist_ok=True)


def download_audio(video_url: str):
    """
    Download a YouTube video's audio.

    Returns:
        {
            "video_id": "...",
            "title": "...",
            "audio_path": "..."
        }
    """

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(VIDEOS_DIR / "%(id)s.%(ext)s"),
        "quiet": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        audio_path = ydl.prepare_filename(info)

    return {
        "video_id": info["id"],
        "title": info["title"],
        "audio_path": audio_path,
    }


if __name__ == "__main__":
    url = input("Paste YouTube URL: ")
    result = download_audio(url)
    print(result)