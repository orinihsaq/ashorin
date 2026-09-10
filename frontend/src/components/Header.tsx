import React from 'react';
import {
  Moon,
  Sun,
  Cpu,
  ClockCounterClockwise,
  ArrowSquareOut,
} from '@phosphor-icons/react';
import { SystemInfoResponse } from '../types';

interface HeaderProps {
  theme: 'dark' | 'light';
  onToggleTheme: () => void;
  onOpenSystemInfo: () => void;
  onToggleHistory: () => void;
  historyCount: number;
  systemInfo: SystemInfoResponse | null;
}

export const Header: React.FC<HeaderProps> = ({
  theme,
  onToggleTheme,
  onOpenSystemInfo,
  onToggleHistory,
  historyCount,
  systemInfo,
}) => {
  return (
    <header className="sticky top-0 z-30 w-full border-b border-zinc-200 dark:border-zinc-800/80 bg-white/85 dark:bg-zinc-950/85 backdrop-blur-md transition-colors">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3">
          <div className="relative group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 via-brand-600 to-purple-600 flex items-center justify-center text-white shadow-md shadow-brand-500/20 ring-1 ring-white/20 transition-transform group-hover:scale-105">
              <span className="font-mono font-black text-lg tracking-tighter leading-none select-none">
                a<span className="text-amber-300">N</span>
              </span>
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-zinc-950" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-zinc-900 dark:text-zinc-50 font-sans">
                ashori<span className="text-brand-600 dark:text-brand-400 font-black">N</span>
              </span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider rounded-md bg-brand-50 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60">
                PRO UTILITY
              </span>
            </div>
            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 hidden sm:flex items-center gap-1.5 leading-none mt-0.5">
              <span>Precision Media Extraction</span>
              <span className="text-zinc-300 dark:text-zinc-700">•</span>
              <span className="font-mono">yt-dlp + FFmpeg</span>
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* History drawer trigger */}
          <button
            onClick={onToggleHistory}
            className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 bg-zinc-100/80 dark:bg-zinc-900/80 hover:bg-zinc-200/80 dark:hover:bg-zinc-800 border border-zinc-200/80 dark:border-zinc-800 transition"
            title="Download History"
            aria-label="Download History"
          >
            <ClockCounterClockwise size={16} className="text-zinc-500 dark:text-zinc-400" />
            <span className="hidden md:inline">History</span>
            {historyCount > 0 && (
              <span className="ml-0.5 px-1.5 py-0.2 text-[10px] font-mono font-bold rounded-full bg-brand-600 text-white leading-tight">
                {historyCount}
              </span>
            )}
          </button>

          {/* System Diagnostics trigger */}
          <button
            onClick={onOpenSystemInfo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:text-zinc-900 dark:hover:text-zinc-100 bg-zinc-100/80 dark:bg-zinc-900/80 hover:bg-zinc-200/80 dark:hover:bg-zinc-800 border border-zinc-200/80 dark:border-zinc-800 transition"
            title="Engine & Storage Diagnostics"
            aria-label="System Diagnostics"
          >
            <Cpu size={16} className="text-brand-500" />
            <span className="hidden sm:inline font-mono">
              {systemInfo?.ytdlp_version ? `v${systemInfo.ytdlp_version.slice(0, 8)}` : 'Engine'}
            </span>
            <span
              className={`w-2 h-2 rounded-full ${
                systemInfo?.ffmpeg_available ? 'bg-emerald-500 shadow-xs shadow-emerald-500/50' : 'bg-amber-500'
              }`}
              title={systemInfo?.ffmpeg_available ? 'FFmpeg Ready' : 'FFmpeg Unavailable'}
            />
          </button>

          {/* API Docs link */}
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="hidden lg:flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-xs font-medium text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          >
            <span>API</span>
            <ArrowSquareOut size={12} />
          </a>

          {/* Theme toggle */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-xl text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-transparent hover:border-zinc-200 dark:hover:border-zinc-800 transition"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <Sun size={18} weight="fill" className="text-amber-400" />
            ) : (
              <Moon size={18} weight="bold" className="text-zinc-700" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
