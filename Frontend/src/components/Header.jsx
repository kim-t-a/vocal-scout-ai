import { motion } from "framer-motion";
import { ScanSearch, Moon, Sun, Github } from "lucide-react";

export default function Header({ dark, onToggleDark }) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/40 dark:border-white/5 bg-white/60 dark:bg-surface-dark/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <a
          href="#"
          onClick={(e) => e.preventDefault()}
          className="focus-ring rounded-lg flex items-center gap-2.5"
          aria-label="VocalScout home"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary-blue shadow-lg shadow-primary/30">
            <ScanSearch className="h-5 w-5 text-white" aria-hidden="true" />
          </span>
          <span className="text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
            Vocal<span className="text-gradient">Scout</span>
          </span>
        </a>

        <div className="flex items-center gap-2">
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            aria-label="View source on GitHub"
            className="focus-ring rounded-lg p-2.5 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
          >
            <Github className="h-5 w-5" aria-hidden="true" />
          </a>
          <button
            type="button"
            onClick={onToggleDark}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            className="focus-ring rounded-lg p-2.5 text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
          >
            {dark ? (
              <Sun className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Moon className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
