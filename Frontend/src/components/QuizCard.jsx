import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardList,
  RotateCcw,
  Quote,
  SkipForward,
  Check,
  X,
  Award,
} from "lucide-react";
import { formatTime } from "../utils/formatTime";

/**
 * Interactive multiple-choice quiz. The backend now sends structured
 * {question, options[4], answer_index} items parsed from the model's JSON
 * output; the user picks an option per question and gets a score at the end.
 * "Jump" still seeks the player to the transcript moment the quiz came from.
 */
export default function QuizCard({ questions, timestamp, quote, onJump }) {
  const [picked, setPicked] = useState(() => questions?.map(() => null));
  const [resetKey, setResetKey] = useState(0);

  if (!questions?.length) return null;

  const answeredCount = picked.filter((p) => p !== null).length;
  const allAnswered = answeredCount === questions.length;
  const score = picked.filter(
    (p, i) => p !== null && p === questions[i].answer_index
  ).length;

  const pick = (qi, oi) =>
    setPicked((prev) => prev.map((p, i) => (i === qi ? oi : p)));

  const reset = () => {
    setPicked(questions.map(() => null));
    setResetKey((k) => k + 1);
  };

  const scoreTone =
    score === questions.length
      ? "text-emerald-600 dark:text-emerald-400"
      : score === 0
        ? "text-red-600 dark:text-red-400"
        : "text-amber-600 dark:text-amber-400";

  return (
    <motion.section
      aria-live="polite"
      key={resetKey}
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
              {allAnswered
                ? "All answered — see your score below"
                : `${answeredCount} of ${questions.length} answered`}
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={reset}
          aria-label="Reset quiz"
          className="focus-ring rounded-lg p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {/* questions */}
      <ol className="mt-5 space-y-4">
        {questions.map((q, qi) => {
          const chosen = picked[qi];
          const isAnswered = chosen !== null;
          const isCorrect = chosen === q.answer_index;

          return (
            <motion.li
              key={qi}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * qi, duration: 0.35, ease: "easeOut" }}
              className="rounded-xl border border-slate-200/80 dark:border-white/10 bg-white/60 dark:bg-slate-900/50 p-4"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 text-xs font-bold text-white">
                  {qi + 1}
                </span>
                <p className="text-[15px] font-medium leading-relaxed text-slate-800 dark:text-slate-200">
                  {q.question}
                </p>
              </div>

              {/* options */}
              <div className="mt-3 ml-9 space-y-2" role="radiogroup" aria-label={`Question ${qi + 1} options`}>
                {q.options.map((option, oi) => {
                  const isPicked = chosen === oi;
                  const isRight = isAnswered && oi === q.answer_index;
                  const isWrongPick = isAnswered && isPicked && !isCorrect;

                  let optionClass =
                    "border-slate-200 dark:border-white/10 bg-white/70 dark:bg-slate-800/70 hover:border-emerald-400/50";
                  if (isAnswered) {
                    if (isRight)
                      optionClass =
                        "border-emerald-400 bg-emerald-400/10 text-emerald-700 dark:text-emerald-300";
                    else if (isWrongPick)
                      optionClass =
                        "border-red-400 bg-red-400/10 text-red-700 dark:text-red-300";
                    else
                      optionClass =
                        "border-slate-200 dark:border-white/10 bg-white/40 dark:bg-slate-800/40 opacity-60";
                  }

                  return (
                    <button
                      key={oi}
                      type="button"
                      role="radio"
                      aria-checked={isPicked}
                      disabled={isAnswered}
                      onClick={() => pick(qi, oi)}
                      className={`focus-ring flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left text-sm transition-colors disabled:cursor-default ${optionClass}`}
                    >
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-[10px] font-bold">
                        {String.fromCharCode(65 + oi)}
                      </span>
                      <span className="flex-1">{option}</span>
                      {isRight && (
                        <Check className="h-4 w-4 shrink-0" aria-hidden="true" />
                      )}
                      {isWrongPick && (
                        <X className="h-4 w-4 shrink-0" aria-hidden="true" />
                      )}
                    </button>
                  );
                })}
              </div>
            </motion.li>
          );
        })}
      </ol>

      {/* score summary */}
      <AnimatePresence>
        {allAnswered && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="mt-5 flex items-center gap-3 rounded-xl border border-emerald-400/40 bg-emerald-400/10 p-4">
              <Award className="h-6 w-6 shrink-0 text-emerald-500" aria-hidden="true" />
              <div>
                <p className="text-sm font-bold text-slate-900 dark:text-white">
                  You scored {score} / {questions.length}
                </p>
                <p className={`text-xs font-medium ${scoreTone}`}>
                  {score === questions.length
                    ? "Perfect — you were paying attention!"
                    : score >= questions.length / 2
                      ? "Solid — review the ones you missed below."
                      : "Worth re-watching the relevant part — jump below!"}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* footer actions */}
      <div className="mt-5 flex items-center gap-2">
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
