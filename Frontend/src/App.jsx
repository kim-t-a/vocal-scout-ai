import { useCallback, useEffect, useRef, useState } from "react";
import { askQuestionStream, processVideo, getVideoStatus, getCurrentVideo } from "./api";
import { getYouTubeId } from "./utils/getYouTubeId";
import { formatTime } from "./utils/formatTime";
import AuroraBackground from "./components/AuroraBackground";
import Header from "./components/Header";
import Hero from "./components/Hero";
import VideoPlayer from "./components/VideoPlayer";
import TranscriptPanel from "./components/TranscriptPanel";
import VideoLoader from "./components/VideoLoader";
import SearchBox from "./components/SearchBox";
import LoadingCard from "./components/LoadingCard";
import AnswerCard from "./components/AnswerCard";
import QuizCard from "./components/QuizCard";
import SuggestionChips from "./components/SuggestionChips";
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
  // id of the assistant message whose tokens are still arriving (null = idle)
  const [streamingId, setStreamingId] = useState(null);
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

  // Current playback position for the transcript panel's active-chunk
  // highlight. Stable callback — the panel polls it on its own interval.
  const getPlayerTime = useCallback(() => {
    const player = playerRef.current;
    if (!player?.isReady?.()) return null;
    try {
      const seconds = player.getCurrentTime();
      return typeof seconds === "number" ? seconds : null;
    } catch {
      return null;
    }
  }, []);

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
    async (rawQuestion, quizCount = null) => {
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

      // The reply card is added as soon as the backend sends `meta`, then
      // grown one `token` event at a time, so the answer types itself out.
      const placeholderId = Date.now() + 1;
      let placeholderAdded = false;

      const patchPlaceholder = (fields) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === placeholderId ? { ...m, ...fields } : m))
        );

      const handleEvent = (event) => {
        if (event.type === "meta") {
          placeholderAdded = true;
          setStreamingId(placeholderId);
          setMessages((prev) => [
            ...prev,
            {
              id: placeholderId,
              role: "assistant",
              type: "answer",
              answer: "",
              timestamp: event.timestamp ?? 0,
              quote: event.quote ?? "",
            },
          ]);
          return;
        }

        if (event.type === "token") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === placeholderId
                ? { ...m, answer: (m.answer || "") + (event.text || "") }
                : m
            )
          );
          return;
        }

        if (event.type === "suggestions") {
          patchPlaceholder({ suggestions: event.suggestions });
          return;
        }

        if (event.type === "done") return;

        // quiz / notice / clarification / error are complete messages. Only
        // merge the fields they actually carry — quote and timestamp came
        // with `meta` (or aren't meaningful for a notice).
        const fields = {
          type: event.type || "answer",
          answer: event.answer ?? "",
        };
        if (event.quote !== undefined) fields.quote = event.quote;
        if (event.timestamp !== undefined) fields.timestamp = event.timestamp;
        if (event.questions) fields.questions = event.questions;

        if (placeholderAdded) {
          patchPlaceholder(fields);
        } else {
          placeholderAdded = true;
          setMessages((prev) => [
            ...prev,
            { id: placeholderId, role: "assistant", quote: "", timestamp: 0, ...fields },
          ]);
        }

        // The tutor asked the user something — put the cursor in the box.
        if (fields.type === "clarification") searchRef.current?.focus();
      };

      try {
        // Send the last few exchanges so the tutor understands follow-ups.
        const history = messages.slice(-MAX_HISTORY).map(({ role, content, answer }) => ({
          role,
          content: role === "assistant" ? answer : content,
        }));

        await askQuestionStream(trimmed, videoId, history, quizCount, handleEvent);

        if (!placeholderAdded) {
          showToast("error", "The tutor sent back an empty answer. Please try again.");
        }
      } catch (err) {
        if (err?.status) {
          showToast("error", `Backend error (${err.status}). Check the server logs.`);
        } else {
          showToast("error", "Can't reach the backend. Is it running on http://127.0.0.1:8000 ?");
        }
      } finally {
        setStreamingId(null);
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

  // Clicking a follow-up chip asks that question immediately.
  const handleSuggestionPick = useCallback(
    (suggestion) => {
      if (loading) return;
      submitQuestion(suggestion);
    },
    [loading, submitQuestion]
  );

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
          <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 sm:px-6 lg:flex-row lg:items-start">
            <div className="min-w-0 flex-1">
              <VideoPlayer ref={playerRef} videoId={videoId} />
            </div>
            <div className="w-full shrink-0 lg:w-[360px]">
              <TranscriptPanel
                videoId={videoId}
                onSeek={seekTo}
                getTime={getPlayerTime}
              />
            </div>
          </div>
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
            onQuiz={(count) => submitQuestion("quiz me on this video", count)}
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
                streaming={message.id === streamingId}
                onJump={seekTo}
                onRegenerate={regenerate}
              />
            )
          )}

          {/* Follow-up chips under the newest assistant answer only */}
          {!loading &&
            messages.length > 0 &&
            messages[messages.length - 1].role === "assistant" &&
            messages[messages.length - 1].type === "answer" && (
              <SuggestionChips
                suggestions={messages[messages.length - 1].suggestions}
                onPick={handleSuggestionPick}
              />
            )}

          {/* Once the first tokens land the growing answer card replaces the
              skeleton, so the wait is spent reading instead of spinning. */}
          {loading && !streamingId && <LoadingCard />}

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
