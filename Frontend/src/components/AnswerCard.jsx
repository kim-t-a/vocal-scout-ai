import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Quote, Copy, Check, RefreshCw, SkipForward } from "lucide-react";
import { formatTime } from "../utils/formatTime";

/**
 * Premium AI answer card: answer text, supporting quote callout,
 * copy / regenerate actions, and a big Jump-to-timestamp button.
 */
export default function AnswerCard({ answer, quote, timestamp, onJump, onRegenerate }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — ignore */
    }
  };

  return (
    <motion.section
      aria-live="polite"
      initial={{ opacity: 0, y: 28 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      whileHover={{ y: -4 }}
      className="glass relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl p-6 sm:p-8"
    >
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-primary-soft to-primary-blue"
      />
      <AnswerCardBody
        answer={answer}
        quote={quote}
        timestamp={timestamp}
        onJump={onJump}
        onRegenerate={onRegenerate}
        copied={copied}
        onCopy={handleCopy}
      />
    </motion.section>
  );
}

function AnswerCardBody({
  answer,
  quote,
  timestamp,
  onJump,
  onRegenerate,
  copied,
  onCopy,
}) {
  return (
    <>
      {/* header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-blue shadow-lg shadow-primary/30">
            <Sparkles className="h-5 w-5 text-white" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              VocalScout AI
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Answer found in this video
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <motion.button
            type="button"
            onClick={onCopy}
            aria-label="Copy answer to clipboard"
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            className="focus-ring rounded-lg p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
          >
            {copied ? (
              <Check className="h-4 w-4 text-emerald-500" aria-hidden="true" />
            ) : (
              <Copy className="h-4 w-4" aria-hidden="true" />
            )}
          </motion.button>
          <motion.button
            type="button"
            onClick={onRegenerate}
            aria-label="Regenerate answer"
            whileHover={{ scale: 1.08 }}
            whileTap={{ scale: 0.92 }}
            className="focus-ring rounded-lg p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </motion.button>
        </div>
      </div>

      {/* answer body */}
      <p className="mt-5 whitespace-pre-wrap text-[15px] leading-relaxed text-slate-700 dark:text-slate-300">
        {answer}
      </p>

      {/* supporting quote callout */}
      {quote && (
        <blockquote className="mt-5 rounded-xl border-l-4 border-primary/60 bg-primary/5 dark:bg-primary/10 p-4 pl-5">
          <div className="flex items-start gap-3">
            <Quote
              className="mt-0.5 h-4 w-4 shrink-0 text-primary dark:text-primary-soft"
              aria-hidden="true"
            />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary dark:text-primary-soft">
                From the transcript
              </p>
              <p className="mt-1 text-sm italic leading-relaxed text-slate-600 dark:text-slate-400">
                “{quote}”
              </p>
            </div>
          </div>
        </blockquote>
      )}

      {/* jump button */}
      <motion.button
        type="button"
        onClick={() => onJump(timestamp)}
        whileHover={{ scale: 1.03 }}
        whileTap={{ scale: 0.96 }}
        className="btn-gradient mt-6 w-full px-6 py-3.5 text-base"
      >
        <SkipForward className="h-5 w-5" aria-hidden="true" />
        Jump to {formatTime(timestamp)}
      </motion.button>
    </>
  );
}
