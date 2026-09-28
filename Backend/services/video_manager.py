from urllib.parse import urlparse, parse_qs
import chromadb


class VideoManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="chroma_db")

    def extract_video_id(self, url: str) -> str | None:
        """Extract a YouTube video ID from common URL formats."""

        parsed = urlparse(url)

        # https://www.youtube.com/watch?v=...
        if parsed.hostname in ("www.youtube.com", "youtube.com"):
            return parse_qs(parsed.query).get("v", [None])[0]

        # https://youtu.be/...
        if parsed.hostname == "youtu.be":
            return parsed.path.lstrip("/")

        return None

    def collection_name(self, video_id: str) -> str:
        return f"video_{video_id}"

    def collection_exists(self, video_id: str) -> bool:
        """Check whether this video's Chroma collection already exists."""

        name = self.collection_name(video_id)

        collections = self.client.list_collections()

        return any(c.name == name for c in collections)