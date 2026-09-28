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
import QuizCard from "./components/QuizCard";
import UserBubble from "./components/UserBubble";
import EmptyState from "./components/EmptyState";
import Toast from "./components/Toast";
import Footer from "./components/Footer";

// Default demo video — matches the transcript ingested in the backend.
const DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=fUo0HsrLKCk";

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 5 * 60 * 1000;

// Conversation memory: pairs of exchanges sent to the backend as follow-up context.
const MAX_HISTORY = 10;

export default function App() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = window.localStorage.getItem("vocalscout-theme");
    if (saved) return saved === "dark";
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
  });

  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); // { id, role: "user" | "assistant", ... }
  const [loading, setLoading] = useState(false);
  const [lastQuestion, setLastQuestion] = useState("");
  const [toast, setToast] = useState(null);
  const [videoId, setVideoId] = useState(() => getYouTubeId(DEFAULT_VIDEO_URL));

  const playerRef = useRef(null);
  const searchRef = useRef(null);
  const toastTimer = useRef(null);
  const messagesEndRef = useRef(null);

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

  // ---- keep the newest message in view -----------------------------------
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

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

  // ---- seek (imperative handle from VideoPlayer) --------------------------
  const seekTo = useCallback(
    (ms) => {
      const player = playerRef.current;
      if (!player) {
        showToast("error", "Player not ready yet — give it a second and try again.");
        return;
      }
      if (player.isReady()) {
        player.seekTo((Number(ms) || 0) / 1000);
        showToast("success", `Jumped to ${formatTime(ms)}`);
      } else {
        // Queue the seek — it applies as soon as the player finishes loading.
        player.seekTo((Number(ms) || 0) / 1000);
        showToast("success", `Player is loading — will jump to ${formatTime(ms)}`);
      }
      document
        .getElementById("video-section")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    },
    [showToast]
  );

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
          if (status.status === "error") {
            onError?.(status.detail || "Something went wrong while building this tutor. Check the server logs.");
            onDone?.();
            return;
          }
          if (status.status === "not_found") {
            onError?.("The backend has no record of this video — try again.");
            onDone?.();
            return;
          }
        }

        onError?.("Still building after 5 minutes — the video may be too long. Try again shortly.");
        onDone?.();
      } catch (err) {
        const detail = err?.response?.data?.detail;
        if (detail) {
          onError?.(detail);
        } else if (err?.response?.status === 400) {
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

  // ---- ask ---------------------------------------------------------------
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
      setLastQuestion(trimmed);
      setMessages((prev) => [
        ...prev,
        { id: Date.now(), role: "user", content: trimmed },
      ]);

      try {
        // Send the last few exchanges so the tutor understands follow-ups.
        const history = messages.slice(-MAX_HISTORY).map(({ role, content, answer }) => ({
          role,
          content: role === "assistant" ? answer : content,
        }));
        const data = await askQuestion(trimmed, videoId, history);
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now() + 1,
            role: "assistant",
            type: data.type || "answer",
            answer: data.answer,
            quote: data.quote,
            timestamp: data.timestamp,
            questions: data.questions, // quiz mode only
          },
        ]);
        // The tutor asked the user something — put the cursor in the box.
        if (data.type === "clarification") searchRef.current?.focus();
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
    [loading, videoId, messages, showToast]
  );

  // ---- regenerate the latest answer ---------------------------------------
  const regenerate = useCallback(() => {
    if (!lastQuestion || loading) return;
    setMessages((prev) => {
      const next = [...prev];
      const lastAssistant = next.findLastIndex((m) => m.role === "assistant");
      if (lastAssistant !== -1) {
        next.splice(lastAssistant, 1);
        const lastUser = next.findLastIndex((m) => m.role === "user");
        if (lastUser !== -1) next.splice(lastUser, 1);
      }
      return next;
    });
    submitQuestion(lastQuestion);
  }, [lastQuestion, loading, submitQuestion]);

  // New video = new conversation.
  const startNewChat = useCallback(() => {
    setMessages([]);
    setLastQuestion("");
  }, []);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex min-h-screen flex-col">
      <AuroraBackground />
      <Header dark={dark} onToggleDark={() => setDark((d) => !d)} />

      <main className="flex-1">
        <Hero onCtaClick={() => searchRef.current?.focus()} />

        <div id="video-section" className="scroll-mt-20">
          <VideoPlayer ref={playerRef} videoId={videoId} />
        </div>

        <div className="mt-8 sm:mt-10">
          <VideoLoader onReady={buildTutor} onVideoBuilt={startNewChat} />
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
          {hasMessages && (
            <div className="mx-auto flex w-full max-w-3xl justify-end">
              <button
                type="button"
                onClick={startNewChat}
                className="focus-ring rounded-full border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-slate-800/70 px-3.5 py-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 hover:border-primary/40 hover:text-primary dark:hover:text-primary-soft transition-colors"
              >
                New conversation
              </button>
            </div>
          )}

          {messages.map((message) =>
            message.role === "user" ? (
              <UserBubble key={message.id} content={message.content} />
            ) : message.type === "quiz" && message.questions ? (
              <QuizCard
                key={message.id}
                questions={message.questions}
                timestamp={message.timestamp}
                quote={message.quote}
                onJump={seekTo}
              />
            ) : (
              <AnswerCard
                key={message.id}
                type={message.type}
                answer={message.answer}
                quote={message.quote}
                timestamp={message.timestamp}
                onJump={seekTo}
              />
            )
          )}

          {loading && <LoadingCard />}

          {!loading && !hasMessages && (
            <EmptyState
              onPickExample={(q) => {
                if (q === "__quiz__") {
                  submitQuestion("quiz me on this video");
                  return;
                }
                setQuestion(q);
                submitQuestion(q);
              }}
            />
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      <Footer />
      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
