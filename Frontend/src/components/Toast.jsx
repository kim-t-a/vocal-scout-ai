import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, X } from "lucide-react";

/**
 * Minimal toast system. Usage:
 *   <Toast toast={toast} onDismiss={...} />
 * where toast = { id, type: "error" | "success", message }
 */
export default function Toast({ toast, onDismiss }) {
  return (
    <div
      aria-live="assertive"
      className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center px-4"
    >
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            role="status"
            className={`pointer-events-auto flex max-w-md items-start gap-3 rounded-xl border p-4 shadow-2xl backdrop-blur-xl ${
              toast.type === "error"
                ? "border-red-200 dark:border-red-500/30 bg-red-50/90 dark:bg-red-950/80"
                : "border-emerald-200 dark:border-emerald-500/30 bg-emerald-50/90 dark:bg-emerald-950/80"
            }`}
          >
            {toast.type === "error" ? (
              <AlertTriangle
                className="mt-0.5 h-5 w-5 shrink-0 text-red-500"
                aria-hidden="true"
              />
            ) : (
              <CheckCircle2
                className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500"
                aria-hidden="true"
              />
            )}
            <p className="text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-200">
              {toast.message}
            </p>
            <button
              type="button"
              onClick={onDismiss}
              aria-label="Dismiss notification"
              className="focus-ring rounded-md p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
