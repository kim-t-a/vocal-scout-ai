from urllib.parse import urlparse, parse_qs
import re
import chromadb


class VideoManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="chroma_db")

    def extract_video_id(self, url: str) -> str | None:
        """Extract a YouTube video ID from common URL formats."""

        if not url:
            return None

        url = url.strip()

        # A raw 11-character video ID
        if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
            return url

        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        parts = [p for p in parsed.path.split("/") if p]

        # https://www.youtube.com/watch?v=...
        if host in ("www.youtube.com", "youtube.com", "m.youtube.com",
                    "music.youtube.com"):
            video_id = parse_qs(parsed.query).get("v", [None])[0]
            if video_id:
                return video_id

            # https://www.youtube.com/shorts/<id>, /live/<id>, /embed/<id>
            if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed"):
                return parts[1].split("?")[0]

        # https://youtu.be/<id>
        if host == "youtu.be" and parts:
            return parts[0].split("?")[0]

        return None

    def collection_name(self, video_id: str) -> str:
        return f"video_{video_id}"

    def collection_exists(self, video_id: str) -> bool:
        """Check whether this video's Chroma collection already exists."""

        name = self.collection_name(video_id)

        collections = self.client.list_collections()

        return any(c.name == name for c in collections)
