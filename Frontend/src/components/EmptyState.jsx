import { motion } from "framer-motion";
import { ClipboardList, MessageCircleQuestion, Sparkles } from "lucide-react";

const EXAMPLES = [
  "How do Python lists work?",
  "What are tuples and when should I use them?",
  "Explain dictionaries in 10 seconds",
  "What is the difference between a list and a tuple?",
];

/** Friendly empty state shown before the first question is asked. */
export default function EmptyState({ onPickExample }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut", delay: 0.25 }}
      className="mx-auto w-full max-w-3xl rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white/40 dark:bg-slate-900/30 p-8 text-center"
      aria-label="No question asked yet"
    >
      <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/15 to-primary-blue/15 ring-1 ring-primary/20">
        <MessageCircleQuestion
          className="h-7 w-7 text-primary dark:text-primary-soft"
          aria-hidden="true"
        />
      </span>
      <h2 className="mt-4 text-lg font-bold text-slate-900 dark:text-white">
        No questions yet
      </h2>
      <p className="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-slate-500 dark:text-slate-400">
        Ask anything about the video and VocalScout will find the exact moment
        it&apos;s explained.
      </p>

      <div className="mt-5 flex flex-wrap justify-center gap-2">
        <motion.button
          type="button"
          onClick={() => onPickExample("__quiz__")}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.32 }}
          whileHover={{ scale: 1.04, y: -2 }}
          whileTap={{ scale: 0.96 }}
          className="focus-ring inline-flex items-center gap-1.5 rounded-full border border-emerald-300/60 dark:border-emerald-400/20 bg-emerald-50/70 dark:bg-emerald-500/10 px-3.5 py-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 hover:border-emerald-400/60 hover:bg-emerald-100/70 dark:hover:bg-emerald-500/20 transition-colors"
        >
          <ClipboardList className="h-3 w-3" aria-hidden="true" />
          Quiz me on this video
        </motion.button>

        {EXAMPLES.map((example, i) => (
          <motion.button
            key={example}
            type="button"
            onClick={() => onPickExample(example)}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.35 + i * 0.07 }}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.96 }}
            className="focus-ring inline-flex items-center gap-1.5 rounded-full border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-slate-800/70 px-3.5 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:border-primary/40 hover:text-primary dark:hover:text-primary-soft transition-colors"
          >
            <Sparkles className="h-3 w-3" aria-hidden="true" />
            {example}
          </motion.button>
        ))}
      </div>
    </motion.section>
  );
}
