/**
 * Extract a YouTube video ID from a URL (or a raw ID).
 * Supports watch?v=, youtu.be/, /shorts/, /embed/ forms.
 * Returns null when nothing matches.
 */
export function getYouTubeId(input) {
  if (!input) return null;
  const value = String(input).trim();

  if (/^[a-zA-Z0-9_-]{11}$/.test(value)) return value;

  try {
    const url = new URL(value);
    if (url.hostname.includes("youtu.be")) {
      return url.pathname.split("/").filter(Boolean)[0] || null;
    }
    if (url.searchParams.get("v")) return url.searchParams.get("v");
    const parts = url.pathname.split("/").filter(Boolean);
    const marker = parts.findIndex((p) => ["shorts", "embed", "live"].includes(p));
    if (marker !== -1 && parts[marker + 1]) {
      return parts[marker + 1].split(/[?&]/)[0];
    }
  } catch {
    return null;
  }
  return null;
}
