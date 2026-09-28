import { useState } from "react";
import { motion } from "framer-motion";
import { Link2, Loader2, WandSparkles, CheckCircle2 } from "lucide-react";

const STAGE_COPY = {
  queued: "Queued — starting up",
  downloading: "Downloading audio",
  transcribing: "Transcribing the lesson",
  chunking: "Organizing into study sections",
  embedding: "Building the searchable tutor",
  ready: "Tutor ready",
};

const STAGE_ORDER = ["queued", "downloading", "transcribing", "chunking", "embedding"];

/**
 * Paste a YouTube URL to build an AI tutor. While the backend ingests the
 * video, show live stage progress. onReady fires with the videoId so the
 * parent can swap the player.
 */
export default function VideoLoader({ onReady, onVideoBuilt, disabled }) {
  const [url, setUrl] = useState("");
  const [building, setBuilding] = useState(false);
  const [stage, setStage] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url.trim() || building) return;
    setBuilding(true);
    setError(null);
    setStage(null);
    // New video -> new conversation: reset the chat before building.
    onVideoBuilt?.();
    onReady({ url: url.trim(), setStage, onError: setError, onDone: () => setBuilding(false) });
  };

  const stageIndex = STAGE_ORDER.indexOf(stage);
  const showProgress = building && stage && stage !== "ready";

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut", delay: 0.08 }}
      className="mx-auto w-full max-w-3xl"
      role="search"
      aria-label="Build an AI tutor from a YouTube URL"
    >
      <div className="flex items-center gap-2 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl p-2 pl-5 shadow-lg">
        <label htmlFor="video-url-input" className="sr-only">
          Paste a YouTube URL
        </label>
        <Link2 className="h-5 w-5 shrink-0 text-slate-400 dark:text-slate-500" aria-hidden="true" />
        <input
          id="video-url-input"
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste a YouTube URL to build your AI tutor..."
          autoComplete="off"
          spellCheck={false}
          maxLength={300}
          disabled={disabled || building}
          className="min-w-0 flex-1 bg-transparent py-2.5 text-base text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none disabled:opacity-60"
        />
        <motion.button
          type="submit"
          disabled={disabled || building || !url.trim()}
          aria-label="Build AI tutor from this video"
          whileHover={building ? undefined : { scale: 1.04 }}
          whileTap={building ? undefined : { scale: 0.96 }}
          className="btn-gradient inline-flex h-11 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {building ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <WandSparkles className="h-4 w-4" aria-hidden="true" />
          )}
          {building ? "Building..." : "Build tutor"}
        </motion.button>
      </div>

      {showProgress && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass mt-3 rounded-xl p-4"
          aria-live="polite"
        >
          <div className="space-y-2">
            {STAGE_ORDER.map((s, i) => {
              const done = stageIndex > i;
              const active = stageIndex === i;
              if (stageIndex < 0) return null;
              return (
                <div key={s} className="flex items-center gap-2.5 text-sm">
                  {done ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-hidden="true" />
                  ) : (
                    <Loader2
                      className={`h-4 w-4 ${active ? "animate-spin text-primary dark:text-primary-soft" : "text-slate-300 dark:text-slate-600"}`}
                      aria-hidden="true"
                    />
                  )}
                  <span
                    className={
                      done
                        ? "text-slate-500 dark:text-slate-400"
                        : active
                          ? "font-semibold text-slate-900 dark:text-white"
                          : "text-slate-400 dark:text-slate-600"
                    }
                  >
                    {STAGE_COPY[s]}
                  </span>
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {error && (
        <p className="mt-2 rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </motion.form>
  );
}
