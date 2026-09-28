import { ScanSearch } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-200/60 dark:border-white/5 py-8">
      <div className="mx-auto flex max-w-6xl flex-col items-center gap-2 px-4 text-center sm:px-6">
        <span className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
          <ScanSearch className="h-4 w-4 text-primary" aria-hidden="true" />
          VocalScout
        </span>
        <p className="text-xs text-slate-500 dark:text-slate-500">
          Built with NVIDIA Nemotron, ChromaDB &amp; AssemblyAI · Hackathon 2026
        </p>
      </div>
    </footer>
  );
}
