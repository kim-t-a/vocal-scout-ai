import { motion } from "framer-motion";
import { User } from "lucide-react";

/** Right-aligned bubble showing the viewer's question in the chat flow. */
export default function UserBubble({ content }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="mx-auto flex w-full max-w-3xl justify-end"
    >
      <div className="flex max-w-[85%] items-start gap-2.5">
        <div className="rounded-2xl rounded-br-sm bg-gradient-to-br from-primary to-primary-blue px-4 py-2.5 text-sm font-medium leading-relaxed text-white shadow-lg shadow-primary/25">
          {content}
        </div>
        <span
          aria-hidden="true"
          className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-200/80 dark:bg-slate-800"
        >
          <User className="h-4 w-4 text-slate-500 dark:text-slate-400" />
        </span>
      </div>
    </motion.div>
  );
}
