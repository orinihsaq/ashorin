import React from 'react';
import {
  DownloadSimple,
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
    <header className="sticky top-0 z-30 w-full border-b border-zinc-200 dark:border-zinc-800/80 bg-white/80 dark:bg-zinc-950/80 backdrop-blur-md transition-colors">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Logo and Name */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shadow-sm shadow-brand-500/20">
            <DownloadSimple size={22} weight="bold" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
                Media Downloader Pro
              </h1>
              <span className="hidden sm:inline-flex px-1.5 py-0.5 text-[11px] font-medium rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
                v1.0.0
              </span>
            </div>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 hidden sm:block">
              Self-hosted yt-dlp & FFmpeg engine
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* History button */}
          <button
            onClick={onToggleHistory}
            className="relative p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
            title="Download History"
            aria-label="Download History"
          >
            <ClockCounterClockwise size={20} />
            {historyCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-brand-500" />
            )}
          </button>

          {/* System Info / Engine Status */}
          <button
            onClick={onOpenSystemInfo}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-800 transition"
            title="System Status"
            aria-label="System Status"
          >
            <Cpu size={16} className="text-brand-500" />
            <span className="hidden md:inline">
              yt-dlp {systemInfo?.ytdlp_version ? systemInfo.ytdlp_version.split('.')[0] : ''}
            </span>
            <span
              className={`w-2 h-2 rounded-full ${
                systemInfo?.ffmpeg_available ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
          </button>

          {/* OpenAPI Docs Link */}
          <a
            href="/docs"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          >
            <span>API</span>
            <ArrowSquareOut size={13} />
          </a>

          {/* Theme Toggle */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? (
              <Sun size={20} className="text-amber-400" />
            ) : (
              <Moon size={20} className="text-zinc-700" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
