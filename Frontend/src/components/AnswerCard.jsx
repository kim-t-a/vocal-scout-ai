import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { motion } from "framer-motion";
import {
  Sparkles,
  Quote,
  Copy,
  Check,
  RefreshCw,
  SkipForward,
  HelpCircle,
  Info,
  AlertTriangle,
} from "lucide-react";
import { formatTime } from "../utils/formatTime";

/**
 * AI reply as a chat message. The backend tags each response with a `type`,
 * and each type is presented differently so the user can tell whether the
 * tutor ANSWERED from the transcript, is ASKING for clarification, has a
 * NOTICE (e.g. video still processing), or hit an ERROR.
 *
 *  - answer:        transcript-grounded answer + quote + Jump button
 *  - clarification: the tutor needs more detail (input is focused by App)
 *  - notice:        status info, no transcript involvement
 *  - error:         transient failure — retry via regenerate
 */
const VARIANTS = {
  answer: {
    bar: "bg-gradient-to-r from-primary via-primary-soft to-primary-blue",
    icon: Sparkles,
    iconBg: "bg-gradient-to-br from-primary to-primary-blue shadow-lg shadow-primary/30",
    title: "VocalScout AI",
    subtitle: "Answer found in this video",
  },
  clarification: {
    bar: "bg-gradient-to-r from-amber-400 to-orange-400",
    icon: HelpCircle,
    iconBg: "bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-500/30",
    title: "Needs a little more detail",
    subtitle: "The tutor is asking you a question",
  },
  notice: {
    bar: "bg-gradient-to-r from-sky-400 to-blue-500",
    icon: Info,
    iconBg: "bg-gradient-to-br from-sky-400 to-blue-500 shadow-lg shadow-sky-500/30",
    title: "VocalScout AI",
    subtitle: "Status update",
  },
  error: {
    bar: "bg-gradient-to-r from-red-400 to-rose-500",
    icon: AlertTriangle,
    iconBg: "bg-gradient-to-br from-red-400 to-rose-500 shadow-lg shadow-red-500/30",
    title: "Something went wrong",
    subtitle: "The tutor couldn't answer right now",
  },
};

export default function AnswerCard({
  answer,
  quote,
  timestamp,
  type = "answer",
  streaming = false,
  onJump,
  onRegenerate,
}) {
  const [copied, setCopied] = useState(false);

  const variant = VARIANTS[type] ?? VARIANTS.answer;
  const Icon = variant.icon;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — ignore */
    }
  };

  const canJump = type === "answer" && Number(timestamp) > 0;
  const canCopy = type === "answer";
  const canRegenerate = type === "answer" || type === "error";

  return (
    <motion.section
      aria-live="polite"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="glass relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl p-5 sm:p-6"
    >
      <div aria-hidden="true" className={`absolute inset-x-0 top-0 h-1 ${variant.bar}`} />

      {/* header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-white ${variant.iconBg}`}
          >
            <Icon className="h-4.5 w-4.5" aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white">
              {variant.title}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {variant.subtitle}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {canCopy && (
            <motion.button
              type="button"
              onClick={handleCopy}
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
          )}
          {canRegenerate && onRegenerate && (
            <motion.button
              type="button"
              onClick={onRegenerate}
              aria-label={type === "error" ? "Retry" : "Regenerate answer"}
              whileHover={{ scale: 1.08 }}
              whileTap={{ scale: 0.92 }}
              className="focus-ring rounded-lg p-2 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            </motion.button>
          )}
        </div>
      </div>

      {/* message body — the model returns markdown (lists, tables for
          compare mode, bold); render it instead of showing raw pipes. */}
      <MarkdownContent text={answer} streaming={streaming} />

      {/* supporting quote callout */}
      {quote && (
        <blockquote className="mt-4 rounded-xl border-l-4 border-primary/60 bg-primary/5 p-4 pl-5 dark:bg-primary/10">
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
                &ldquo;{quote}&rdquo;
              </p>
            </div>
          </div>
        </blockquote>
      )}

      {/* jump button */}
      {canJump && (
        <motion.button
          type="button"
          onClick={() => onJump(timestamp)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          className="btn-gradient mt-5 w-full px-6 py-3 text-sm sm:text-base"
        >
          <SkipForward className="h-4.5 w-4.5" aria-hidden="true" />
          Jump to {formatTime(timestamp)}
        </motion.button>
      )}
    </motion.section>
  );
}

/**
 * Shared markdown styling. Kept minimal — typography is inherited from the
 * card, so we only add structure (lists, tables, code) that plain text can't
 * express. remark-gfm enables the pipe tables the compare mode relies on.
 */
export function MarkdownContent({ text, streaming = false }) {
  return (
    <div className="mt-4 text-[15px] leading-relaxed text-slate-700 dark:text-slate-300 [&_a]:text-primary [&_a]:underline [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px] dark:[&_code]:bg-slate-800 [&_li]:ml-4 [&_li]:list-disc [&_ol_li]:list-decimal [&_strong]:font-semibold [&_strong]:text-slate-900 dark:[&_strong]:text-white [&_table]:mt-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-sm [&_td]:border [&_td]:border-slate-200 [&_td]:px-2.5 [&_td]:py-1.5 [&_td]:align-top dark:[&_td]:border-white/10 [&_th]:border [&_th]:border-slate-200 [&_th]:bg-slate-50 [&_th]:px-2.5 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-semibold dark:[&_th]:border-white/10 dark:[&_th]:bg-slate-800/60">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{text}</ReactMarkdown>
      {/* blinking caret shown only while the answer is still being written */}
      {streaming && (
        <span
          aria-hidden="true"
          className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-sm bg-primary align-[-2px]"
        />
      )}
    </div>
  );
}
