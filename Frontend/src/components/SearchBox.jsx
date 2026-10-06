import { forwardRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUp, ClipboardList, Loader2 } from "lucide-react";

const QUIZ_COUNTS = [3, 5, 10];

/**
 * Large rounded AI search input. Enter submits; the send button shows
 * a spinner while a question is in flight. A quiz button sits beside the
 * input and opens a small picker so the user chooses how many questions
 * the quiz should have.
 */
const SearchBox = forwardRef(function SearchBox(
  { value, onChange, onSubmit, onQuiz, loading },
  inputRef
) {
  const [focused, setFocused] = useState(false);
  const [quizPickerOpen, setQuizPickerOpen] = useState(false);
  const disabled = loading || !value.trim();

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!disabled) onSubmit(value.trim());
  };

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, ease: "easeOut", delay: 0.18 }}
      className="relative mx-auto w-full max-w-3xl"
      role="search"
    >
      {/* glow ring on focus */}
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute -inset-0.5 rounded-2xl bg-gradient-to-r from-primary via-primary-soft to-primary-blue opacity-0 blur-md transition-opacity duration-300 ${
          focused ? "opacity-40" : ""
        }`}
      />

      <div
        className={`relative flex items-center gap-2 rounded-2xl border bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl p-2 pl-5 shadow-lg transition-colors ${
          focused
            ? "border-primary/50"
            : "border-slate-200/80 dark:border-white/10"
        }`}
      >
        {onQuiz && (
          <div className="relative shrink-0">
            <motion.button
              type="button"
              onClick={() => setQuizPickerOpen((open) => !open)}
              disabled={loading}
              aria-label="Quiz me on this video"
              aria-expanded={quizPickerOpen}
              title="Quiz me on this video"
              whileHover={loading ? undefined : { scale: 1.08 }}
              whileTap={loading ? undefined : { scale: 0.92 }}
              className="focus-ring h-9 w-9 rounded-lg border border-emerald-300/60 dark:border-emerald-400/20 bg-emerald-50/70 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:border-emerald-400/60 hover:bg-emerald-100/70 dark:hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              <ClipboardList className="mx-auto h-4.5 w-4.5" aria-hidden="true" />
            </motion.button>

            <AnimatePresence>
              {quizPickerOpen && (
                <motion.div
                  initial={{ opacity: 0, y: -6, scale: 0.96 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -6, scale: 0.96 }}
                  transition={{ duration: 0.18, ease: "easeOut" }}
                  className="absolute right-0 top-11 z-20 w-44 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 p-2 shadow-xl"
                  role="menu"
                  aria-label="Choose number of quiz questions"
                >
                  <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                    How many questions?
                  </p>
                  {QUIZ_COUNTS.map((count) => (
                    <button
                      key={count}
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        setQuizPickerOpen(false);
                        onQuiz(count);
                      }}
                      className="focus-ring flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-sm text-slate-600 dark:text-slate-300 hover:bg-emerald-50 dark:hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                    >
                      <span>{count} questions</span>
                      <ClipboardList className="h-3.5 w-3.5 opacity-50" aria-hidden="true" />
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        <label htmlFor="question-input" className="sr-only">
          Ask a question about this video
        </label>
        <input
          id="question-input"
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Ask something about this video..."
          autoComplete="off"
          maxLength={400}
          className="min-w-0 flex-1 bg-transparent py-2.5 text-base text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none"
        />

        <kbd className="hidden sm:inline-flex items-center rounded-md border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400 dark:text-slate-500">
          Enter ↵
        </kbd>

        <motion.button
          type="submit"
          disabled={disabled}
          aria-label="Ask the question"
          whileHover={disabled ? undefined : { scale: 1.06 }}
          whileTap={disabled ? undefined : { scale: 0.94 }}
          className="btn-gradient h-11 w-11 shrink-0 rounded-xl disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <ArrowUp className="h-5 w-5" aria-hidden="true" />
          )}
        </motion.button>
      </div>
    </motion.form>
  );
});

export default SearchBox;
