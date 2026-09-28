import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ClipboardList, Eye, EyeOff, RotateCcw, Quote, SkipForward } from "lucide-react";
import { formatTime } from "../utils/formatTime";

/**
 * Interactive quiz card: numbered questions with reveal-the-answer toggles,
 * a reset, and a Jump button to the moment the quiz content came from.
 * Rendered when /ask responds with type "quiz" (structured questions parsed
 * from the model's output on the backend).
 */
export default function QuizCard({ questions, timestamp, onJump }) {
  const [revealed, setRevealed] = useState(() => questions.map(() => false));
  const [allRevealed, setAllRevealed] = useState(false);

  if (!questions?.length) return null;

  const toggle = (i) =>
    setRevealed((prev) => prev.map((r, idx) => (idx === i ? !r : r)));

  const revealAll = () => {
    const next = !allRevealed;
    setAllRevealed(next);
    setRevealed(questions.map(() => next));
  };

  const revealedCount = revealed.filter(Boolean).length;

  return (
    <motion.section
      aria-live="polite"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="glass relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl p-5 sm:p-6"
    >
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-500"
      />

      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 shadow-lg shadow-teal-500/30">
            <ClipboardList className="h-4.5 w-4.5 text-white" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">
              Quiz time
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {revealedCount} of {questions.length} revealed
              {revealedCount < questions.length
                ? " — try answering before you peek"
                : " — nice work!"}
            </p>
          </div>
        </div>

        <motion.button
          type="button"
          onClick={revealAll}
          aria-label={allRevealed ? "Hide all answers" : "Reveal all answers"}
          whileHover={{ scale: 1.06 }}
          whileTap={{ scale: 0.94 }}
          className="focus-ring rounded-lg p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
        >
          {allRevealed ? (
            <EyeOff className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Eye className="h-4 w-4" aria-hidden="true" />
          )}
        </motion.button>
      </div>

      {/* questions */}
      <ol className="mt-5 space-y-4">
        {questions.map((q, i) => (
          <motion.li
            key={i}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i, duration: 0.35, ease: "easeOut" }}
            className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-white/60 dark:bg-slate-900/50 p-4"
          >
            <div className="flex items-start gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 text-xs font-bold text-white">
                {i + 1}
              </span>
              <p className="text-[15px] font-medium leading-relaxed text-slate-800 dark:text-slate-200">
                {q.question}
              </p>
            </div>

            <AnimatePresence initial={false}>
              {revealed[i] && q.answer && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 rounded-lg border-l-4 border-emerald-400/70 bg-emerald-400/10 p-3 pl-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                      Answer
                    </p>
                    <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                      {q.answer}
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {!revealed[i] && q.answer && (
              <button
                type="button"
                onClick={() => toggle(i)}
                className="focus-ring mt-3 ml-9 rounded-full border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-slate-800/70 px-3 py-1 text-xs font-medium text-slate-500 dark:text-slate-400 hover:border-emerald-400/50 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
              >
                Show answer
              </button>
            )}
          </motion.li>
        ))}
      </ol>

      {/* footer actions */}
      <div className="mt-5 flex items-center gap-2">
        <button
          type="button"
          onClick={() => {
            setRevealed(questions.map(() => false));
            setAllRevealed(false);
          }}
          className="focus-ring inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-slate-800/70 px-3.5 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:border-primary/40 hover:text-primary dark:hover:text-primary-soft transition-colors"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          Reset quiz
        </button>

        {Number(timestamp) > 0 && (
          <motion.button
            type="button"
            onClick={() => onJump?.(timestamp)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.97 }}
            className="btn-gradient flex-1 px-6 py-2.5 text-sm"
          >
            <SkipForward className="h-4 w-4" aria-hidden="true" />
            Jump to {formatTime(timestamp)}
          </motion.button>
        )}
      </div>

      {quote && <QuoteFooter quote={quote} />}
    </motion.section>
  );
}

function QuoteFooter({ quote }) {
  return (
    <blockquote className="mt-4 rounded-xl border-l-4 border-primary/60 bg-primary/5 p-4 pl-5 dark:bg-primary/10">
      <div className="flex items-start gap-3">
        <Quote
          className="mt-0.5 h-4 w-4 shrink-0 text-primary dark:text-primary-soft"
          aria-hidden="true"
        />
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-primary dark:text-primary-soft">
            Quiz built from this part of the transcript
          </p>
          <p className="mt-1 text-sm italic leading-relaxed text-slate-600 dark:text-slate-400">
            &ldquo;{quote}&rdquo;
          </p>
        </div>
      </div>
    </blockquote>
  );
}
