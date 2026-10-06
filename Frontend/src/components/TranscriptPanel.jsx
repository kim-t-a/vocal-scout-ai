import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import { getTranscript } from "../api";
import { formatTime } from "../utils/formatTime";

const TIME_POLL_MS = 500;

/**
 * Wrap search matches in <mark>. Splitting is case-insensitive and the
 * query is regex-escaped, so "C++ (v2)" can't blow up the panel.
 */
function highlight(text, query) {
  const q = query.trim();
  if (!q) return text;

  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));

  return parts.map((part, index) =>
    part.toLowerCase() === q.toLowerCase() ? (
      <mark
        key={index}
        className="rounded bg-primary/25 text-inherit dark:bg-primary/30"
      >
        {part}
      </mark>
    ) : (
      <span key={index}>{part}</span>
    )
  );
}

/**
 * Searchable transcript beside the player.
 *
 * Chunks come from the backend's chunk file (the same data retrieval uses).
 * Chunks are grouped under their AssemblyAI chapter headline, every row shows
 * its start timestamp and seeks the player on click, and the chunk currently
 * being spoken is highlighted and kept in view (as long as the parent passes
 * a `getTime` callback).
 */
export default function TranscriptPanel({ videoId, onSeek, getTime }) {
  const [status, setStatus] = useState("loading"); // loading | ready | missing | error | empty
  const [chunks, setChunks] = useState([]);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(true);
  const [currentTime, setCurrentTime] = useState(null);

  const activeRef = useRef(null);

  // Fetch the transcript whenever the video changes.
  useEffect(() => {
    if (!videoId) return;

    let cancelled = false;
    setStatus("loading");
    setChunks([]);

    getTranscript(videoId)
      .then(({ chunks }) => {
        if (cancelled) return;
        setChunks(chunks || []);
        setStatus((chunks || []).length ? "ready" : "empty");
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus(err?.response?.status === 404 ? "missing" : "error");
      });

    return () => {
      cancelled = true;
    };
  }, [videoId]);

  // Poll the player for the playback position — local state, so only this
  // panel re-renders every tick, not the whole app.
  useEffect(() => {
    if (typeof getTime !== "function") return undefined;

    const timer = setInterval(() => {
      const seconds = getTime();
      if (seconds != null) setCurrentTime(seconds);
    }, TIME_POLL_MS);

    return () => clearInterval(timer);
  }, [getTime]);

  // Group consecutive chunks under their chapter headline.
  const groups = useMemo(() => {
    const result = [];
    for (const chunk of chunks) {
      const last = result[result.length - 1];
      if (last && last.chapterIndex === chunk.chapter_index) {
        last.chunks.push(chunk);
      } else {
        result.push({
          chapterIndex: chunk.chapter_index,
          chapter: chunk.chapter,
          chunks: [chunk],
        });
      }
    }
    return result;
  }, [chunks]);

  // Search filter (chapter headers disappear when nothing matches inside).
  const visibleGroups = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((group) => ({
        ...group,
        chunks: group.chunks.filter((chunk) =>
          chunk.text.toLowerCase().includes(q)
        ),
      }))
      .filter((group) => group.chunks.length > 0);
  }, [groups, query]);

  // The chunk currently being spoken.
  const activeId = useMemo(() => {
    if (currentTime == null) return null;
    const playing = chunks.find(
      (chunk) =>
        chunk.start_ms / 1000 <= currentTime && currentTime < chunk.end_ms / 1000
    );
    return playing ? playing.chunk_id : null;
  }, [chunks, currentTime]);

  // Keep the active chunk in view — but never fight the user's own scrolling
  // while they're filtering.
  useEffect(() => {
    if (activeId && !query.trim()) {
      activeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [activeId, query]);

  const busy = status === "loading";

  return (
    <section
      aria-label="Video transcript"
      className="glass overflow-hidden rounded-2xl"
    >
      {/* Header: always visible, doubles as the collapse toggle */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="focus-ring flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-slate-900 dark:text-white">
            Transcript
          </span>
          {status === "ready" && (
            <span className="text-xs text-slate-400 dark:text-slate-500">
              {chunks.length} chunks
            </span>
          )}
        </span>
        {open ? (
          <ChevronUp size={16} className="text-slate-400" />
        ) : (
          <ChevronDown size={16} className="text-slate-400" />
        )}
      </button>

      {open && (
        <>
          {status === "ready" && (
            <div className="px-4 pb-3">
              <div className="relative">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search the transcript..."
                  className="focus-ring w-full rounded-lg border border-slate-200 bg-white/70 py-2 pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
                />
              </div>
              {query.trim() && (
                <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
                  {visibleGroups.reduce((n, g) => n + g.chunks.length, 0)} matches
                </p>
              )}
            </div>
          )}

          <div className="max-h-[460px] overflow-y-auto px-2 pb-3">
            {busy && (
              <p className="px-2 py-6 text-center text-sm text-slate-400">
                Loading transcript...
              </p>
            )}

            {status === "missing" && (
              <p className="px-2 py-6 text-center text-sm leading-relaxed text-slate-400 dark:text-slate-500">
                No transcript yet — build the tutor above to unlock it.
              </p>
            )}

            {status === "error" && (
              <p className="px-2 py-6 text-center text-sm text-slate-400">
                Couldn't load the transcript. Is the backend running?
              </p>
            )}

            {status === "empty" && (
              <p className="px-2 py-6 text-center text-sm text-slate-400">
                This transcript has no text chunks.
              </p>
            )}

            {status === "ready" &&
              visibleGroups.map((group, groupIndex) => (
                <div
                  key={group.chapterIndex >= 0 ? `c${group.chapterIndex}` : `g${groupIndex}`}
                  className="mb-2"
                >
                  {group.chapter && (
                    <h3 className="px-2 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                      {group.chapter}
                    </h3>
                  )}
                  {group.chunks.map((chunk) => {
                    const isActive = chunk.chunk_id === activeId;
                    return (
                      <button
                        key={chunk.chunk_id}
                        ref={isActive ? activeRef : undefined}
                        type="button"
                        onClick={() => onSeek(chunk.start_ms)}
                        className={`focus-ring group flex w-full items-start gap-2 rounded-lg px-2 py-1.5 text-left transition-colors ${
                          isActive
                            ? "bg-primary/10"
                            : "hover:bg-primary/5 dark:hover:bg-white/5"
                        }`}
                      >
                        <span
                          className={`mt-0.5 shrink-0 rounded-md px-1.5 py-0.5 font-mono text-[11px] transition-colors ${
                            isActive
                              ? "bg-primary/20 font-semibold text-primary dark:text-primary-soft"
                              : "bg-slate-100 text-slate-500 group-hover:text-primary dark:bg-white/5 dark:text-slate-400"
                          }`}
                        >
                          {formatTime(chunk.start_ms)}
                        </span>
                        <span className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                          {highlight(chunk.text, query)}
                        </span>
                      </button>
                    );
                  })}
                </div>
              ))}

            {status === "ready" &&
              query.trim() &&
              visibleGroups.length === 0 && (
                <p className="px-2 py-6 text-center text-sm text-slate-400">
                  Nothing in the transcript matches “{query.trim()}”.
                </p>
              )}
          </div>
        </>
      )}
    </section>
  );
}
