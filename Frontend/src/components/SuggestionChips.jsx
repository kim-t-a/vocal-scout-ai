import { motion } from "framer-motion";
import { CornerDownRight } from "lucide-react";

/**
 * Clickable follow-up questions shown under the LATEST assistant answer.
 * Suggestions come from the backend (`suggestions` field on /ask responses),
 * which derives them from the answer text. Only the newest answer shows them
 * to avoid a wall of repeated buttons while scrolling the conversation.
 */
export default function SuggestionChips({ suggestions, onPick }) {
  if (!suggestions?.length) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut", delay: 0.15 }}
      className="mx-auto flex w-full max-w-3xl flex-wrap items-center gap-2 pl-1"
    >
      <CornerDownRight
        className="h-4 w-4 shrink-0 text-slate-400 dark:text-slate-500"
        aria-hidden="true"
      />
      {suggestions.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          onClick={() => onPick?.(suggestion)}
          className="focus-ring rounded-full border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-slate-800/70 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:border-primary/40 hover:text-primary dark:hover:text-primary-soft transition-colors"
        >
          {suggestion}
        </button>
      ))}
    </motion.div>
  );
}
