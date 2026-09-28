import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestion, processVideo, getVideoStatus, getCurrentVideo } from "./api";
import { getYouTubeId } from "./utils/getYouTubeId";
import { formatTime } from "./utils/formatTime";
import AuroraBackground from "./components/AuroraBackground";
import Header from "./components/Header";
import Hero from "./components/Hero";
import VideoPlayer from "./components/VideoPlayer";
import VideoLoader from "./components/VideoLoader";
import SearchBox from "./components/SearchBox";
import LoadingCard from "./components/LoadingCard";
import AnswerCard from "./components/AnswerCard";
import EmptyState from "./components/EmptyState";
import Toast from "./components/Toast";
import Footer from "./components/Footer";

// Default demo video — matches the transcript ingested in the backend.
const DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=fUo0HsrLKCk";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

export default function App() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = window.localStorage.getItem("vocalscout-theme");
    if (saved) return saved === "dark";
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  });

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [lastQuestion, setLastQuestion] = useState("");
  const [toast, setToast] = useState(null);
  const [videoId, setVideoId] = useState(() => getYouTubeId(DEFAULT_VIDEO_URL));

  const playerRef = useRef(null);
  const searchRef = useRef(null);
  const toastTimer = useRef(null);

  // ---- theme -----------------------------------------------------------
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    window.localStorage.setItem("vocalscout-theme", dark ? "dark" : "light");
  }, [dark]);

  // ---- toast helper ----------------------------------------------------
  const showToast = useCallback((type, message, duration = 5000) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ id: Date.now(), type, message });
    toastTimer.current = setTimeout(() => setToast(null), duration);
  }, []);

  useEffect(() => () => clearTimeout(toastTimer.current), []);

  // ---- restore backend's active video on load ---------------------------
  useEffect(() => {
    let cancelled = false;
    getCurrentVideo()
      .then(({ video_id }) => {
        if (!cancelled && video_id) setVideoId(video_id);
      })
      .catch(() => {
        /* backend offline — keep the demo video */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // ---- seek ------------------------------------------------------------
  const seekTo = useCallback((ms) => {
    const player = playerRef.current?.getInternalPlayer?.();
    if (player && typeof player.seekTo === "function") {
      player.seekTo((Number(ms) || 0) / 1000, true);
      if (typeof player.playVideo === "function") player.playVideo();
      showToast("success", `Jumped to ${formatTime(ms)}`);
    } else {
      showToast("error", "Player not ready yet — give it a second and try again.");
    }
  }, [showToast]);

  // ---- build tutor from URL ---------------------------------------------
  const buildTutor = useCallback(
    async ({ url, setStage, onError, onDone }) => {
      try {
        const start = await processVideo(url);
        const id = start.video_id;
        setVideoId(id); // swap the player immediately

        if (start.status === "cached" || start.status === "ready") {
          setStage?.("ready");
          showToast("success", "This video's tutor is ready — ask away!");
          onDone?.();
          return;
        }

        setStage?.("queued");

        // Poll until ingestion finishes (or give up after the timeout).
        const deadline = Date.now() + POLL_TIMEOUT_MS;
        while (Date.now() < deadline) {
          await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
          const status = await getVideoStatus(id);
          setStage?.(status.status);

          if (status.status === "ready") {
            showToast("success", "AI tutor built! Ask anything about this video.");
            onDone?.();
            return;
          }
          if (status.status === "not_found" || status.status === "error") {
            onError?.("The backend stopped processing this video. Check the server logs.");
            onDone?.();
            return;
          }
        }

        onError?.("Still building after 5 minutes — the video may be too long. Try again shortly.");
        onDone?.();
      } catch (err) {
        if (err?.response?.status === 400) {
          onError?.("That doesn't look like a valid YouTube URL.");
        } else if (err?.response) {
          onError?.(`Backend error (${err.response.status}). Check the server logs.`);
        } else {
          onError?.("Can't reach the backend. Is it running on http://127.0.0.1:8000 ?");
        }
        onDone?.();
      }
    },
    [showToast]
  );

  // ---- ask -------------------------------------------------------------
  const submitQuestion = useCallback(
    async (rawQuestion) => {
      const trimmed = rawQuestion.trim();
      if (!trimmed) {
        showToast("error", "Please type a question first.");
        searchRef.current?.focus();
        return;
      }
      if (loading) return;

      setLoading(true);
      setAnswer(null);
      setLastQuestion(trimmed);

      try {
        const data = await askQuestion(trimmed);
        setAnswer(data);
      } catch (err) {
        if (err?.code === "ECONNABORTED") {
          showToast("error", "The request timed out. Try a shorter question.");
        } else if (err?.response) {
          showToast("error", `Backend error (${err.response.status}). Check the server logs.`);
        } else {
          showToast("error", "Can't reach the backend. Is it running on http://127.0.0.1:8000 ?");
        }
      } finally {
        setLoading(false);
      }
    },
    [loading, showToast]
  );

  const regenerate = useCallback(() => {
    if (lastQuestion) submitQuestion(lastQuestion);
  }, [lastQuestion, submitQuestion]);

  return (
    <div className="flex min-h-screen flex-col">
      <AuroraBackground />
      <Header dark={dark} onToggleDark={() => setDark((d) => !d)} />

      <main className="flex-1">
        <Hero onCtaClick={() => searchRef.current?.focus()} />

        <VideoPlayer ref={playerRef} videoId={videoId} />

        <div className="mt-8 sm:mt-10">
          <VideoLoader onReady={buildTutor} />
        </div>

        <div className="mt-8 sm:mt-10">
          <SearchBox
            ref={searchRef}
            value={question}
            onChange={setQuestion}
            onSubmit={submitQuestion}
            loading={loading}
          />
        </div>

        <div className="mt-8 space-y-6 pb-16">
          {loading && <LoadingCard />}

          {!loading && answer && (
            <AnswerCard
              answer={answer.answer}
              quote={answer.quote}
              timestamp={answer.timestamp}
              onJump={seekTo}
              onRegenerate={regenerate}
            />
          )}

          {!loading && !answer && (
            <EmptyState
              onPickExample={(q) => {
                setQuestion(q);
                submitQuestion(q);
              }}
            />
          )}
        </div>
      </main>

      <Footer />
      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
