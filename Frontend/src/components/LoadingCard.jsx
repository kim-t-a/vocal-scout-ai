import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

const BAR_WIDTHS = ["w-11/12", "w-full", "w-4/5"];

/** Shimmer skeleton card shown while the AI searches the transcript. */
export default function LoadingCard() {
  return (
    <motion.section
      aria-live="polite"
      aria-busy="true"
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="glass relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl p-6 sm:p-8"
    >
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-primary via-primary-soft to-primary-blue opacity-70"
      />

      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-blue shadow-lg shadow-primary/30">
          <Sparkles
            className="h-5 w-5 animate-spin text-white [animation-duration:2s]"
            aria-hidden="true"
          />
        </span>
        <p className="text-base font-semibold text-slate-700 dark:text-slate-300">
          Searching the transcript
          <span className="inline-flex w-6 justify-start">
            <motion.span
              animate={{ opacity: [0, 1, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, times: [0, 0.5, 1] }}
            >
              ...
            </motion.span>
          </span>
        </p>
      </div>

      <div className="mt-6 space-y-3">
        {BAR_WIDTHS.map((width, i) => (
          <div
            key={i}
            className={`relative h-4 overflow-hidden rounded-full bg-slate-200/80 dark:bg-slate-700/50 ${width}`}
          >
            <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/60 dark:via-white/10 to-transparent" />
          </div>
        ))}
      </div>
    </motion.section>
  );
}
