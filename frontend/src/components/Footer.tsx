import React from 'react';
import { ShieldCheck, ArrowSquareOut } from '@phosphor-icons/react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-zinc-200 dark:border-zinc-800/80 py-8 mt-20 text-xs text-zinc-500 dark:text-zinc-400 bg-white/40 dark:bg-zinc-950/40 backdrop-blur-xs">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Left: Brand, Dedication & Compliance */}
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-2 sm:gap-4 text-center sm:text-left">
          <div className="flex items-center gap-1.5 font-semibold text-zinc-800 dark:text-zinc-200">
            <span>ashori<span className="text-brand-500">N</span></span>
            <span className="text-zinc-400 dark:text-zinc-600">•</span>
            <span className="text-zinc-600 dark:text-zinc-300 font-medium flex items-center gap-1">
              Made in Love with her ♥
            </span>
          </div>

          <div className="hidden md:flex items-center gap-1 text-[11px] text-zinc-400 dark:text-zinc-500">
            <ShieldCheck size={14} className="text-emerald-500 shrink-0" />
            <span>Authorized media utility • Respect creator copyrights</span>
          </div>
        </div>

        {/* Right: Engine stack & API */}
        <div className="flex items-center gap-3 text-xs">
          <span className="font-mono text-[11px] text-zinc-500 dark:text-zinc-400">
            Powered by yt-dlp + FFmpeg
          </span>
          <span className="text-zinc-300 dark:text-zinc-700">•</span>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-medium hover:text-zinc-900 dark:hover:text-zinc-100 hover:underline transition"
          >
            <span>API Docs</span>
            <ArrowSquareOut size={12} />
          </a>
        </div>
      </div>
    </footer>
  );
};
