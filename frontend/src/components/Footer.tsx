import React from 'react';
import { ShieldCheck } from '@phosphor-icons/react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full border-t border-zinc-200 dark:border-zinc-800/60 py-6 mt-16 text-center text-xs text-zinc-500 dark:text-zinc-400">
      <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 text-zinc-600 dark:text-zinc-400">
          <ShieldCheck size={16} className="text-brand-500" />
          <span>Authorized media extraction utility only. Please respect copyright laws.</span>
        </div>
        <div className="flex items-center gap-4">
          <span>Powered by yt-dlp & FFmpeg</span>
          <span>•</span>
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="hover:underline hover:text-zinc-900 dark:hover:text-zinc-200"
          >
            REST API Docs
          </a>
        </div>
      </div>
    </footer>
  );
};
