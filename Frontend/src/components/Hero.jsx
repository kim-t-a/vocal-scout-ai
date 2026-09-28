import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";

export default function Hero({ onCtaClick }) {
  return (
    <section
      className="relative mx-auto max-w-6xl px-4 pt-14 pb-10 text-center sm:px-6 sm:pt-20"
      aria-labelledby="hero-title"
    >
      {/* floating glow behind hero content */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute left-1/2 top-8 -z-10 h-72 w-[42rem] max-w-full -translate-x-1/2 rounded-full bg-gradient-to-r from-primary/30 via-primary-soft/30 to-primary-blue/30 blur-3xl"
      />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <motion.span
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.4 }}
          className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-white/60 dark:bg-slate-900/60 px-4 py-1.5 text-xs font-semibold text-primary dark:text-primary-soft shadow-sm"
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          AI video answers, powered by NVIDIA Nemotron
        </motion.span>

        <h1
          id="hero-title"
          className="mx-auto mt-6 max-w-3xl text-4xl font-black leading-tight tracking-tight text-slate-900 dark:text-white sm:text-5xl lg:text-6xl"
        >
          Ask a video. <span className="text-gradient">Jump to the answer.</span>
        </h1>

        <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-600 dark:text-slate-400 sm:text-lg">
          Ask any question about a YouTube video and jump directly to the answer.
        </p>

        <motion.button
          type="button"
          onClick={onCtaClick}
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.97 }}
          className="btn-gradient mt-8 px-7 py-3.5 text-base"
        >
          Ask your first question
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        </motion.button>
      </motion.div>
    </section>
  );
}
