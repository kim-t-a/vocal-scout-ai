from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

VIDEOS_DIR = "../videos"


def probe_video(video_url: str):
    """
    Check a YouTube URL is real and downloadable BEFORE starting a
    long download. Raises ValueError with a friendly message when the
    video is unavailable (404), private, region-locked, etc.
    """
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except DownloadError as e:
        message = str(e)

        if "404" in message or "not exist" in message or "unavailable" in message:
            raise ValueError(
                "YouTube says this video doesn't exist (404). "
                "Double-check the link — it may be deleted or mistyped."
            )
        if "private" in message:
            raise ValueError("This video is private, so it can't be processed.")
        if "sign in" in message.lower() or "age" in message.lower():
            raise ValueError(
                "This video requires sign-in/age verification and can't be processed."
            )
        if "regional" in message.lower() or "blocked" in message.lower():
            raise ValueError("This video is blocked in this server's region.")

        raise ValueError(f"Could not read this YouTube video: {message[:200]}")

    if info is None:
        raise ValueError("Could not read this YouTube video.")

    return info


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

    # Fail fast with a clear message before a long download
    probe_video(video_url)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{VIDEOS_DIR}/%(id)s.%(ext)s",
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
