import React, { useState } from 'react';
import {
  LinkSimple,
  ClipboardText,
  X,
  MagnifyingGlass,
  CircleNotch,
  Sparkle,
  Lightning,
  SpeakerHigh,
  FilmStrip,
} from '@phosphor-icons/react';

interface UrlInputProps {
  url: string;
  setUrl: (url: string) => void;
  onAnalyze: (url: string) => void;
  isLoading: boolean;
}

const SAMPLE_URLS = [
  {
    label: 'Big Buck Bunny (YouTube 4K)',
    url: 'https://www.youtube.com/watch?v=aqz-KE-bpKQ',
  },
  {
    label: 'W3C Sample Clip (Direct MP4)',
    url: 'https://www.w3schools.com/html/mov_bbb.mp4',
  },
  {
    label: 'Archive.org Open Media',
    url: 'https://archive.org/download/BigBuckBunny_124/Content/big_buck_bunny_720p_surround.mp4',
  },
];

export const UrlInput: React.FC<UrlInputProps> = ({
  url,
  setUrl,
  onAnalyze,
  isLoading,
}) => {
  const [pasteNotice, setPasteNotice] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim() && !isLoading) {
      onAnalyze(url.trim());
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text.trim());
        setPasteNotice(true);
        setTimeout(() => setPasteNotice(false), 2000);
      }
    } catch {
      // Clipboard permission denied or unsupported
    }
  };

  return (
    <div className="w-full space-y-3.5">
      {/* Search / Input Box */}
      <form onSubmit={handleSubmit} className="relative group">
        <div className="flex flex-col sm:flex-row items-stretch gap-2 p-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-lg shadow-zinc-950/5 dark:shadow-none focus-within:ring-2 focus-within:ring-brand-500/40 focus-within:border-brand-500 transition-all">
          <div className="relative flex-1 flex items-center min-h-[52px] px-3.5">
            <LinkSimple
              size={22}
              className="text-zinc-400 dark:text-zinc-500 shrink-0 mr-3 transition-colors group-focus-within:text-brand-500"
            />
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste media link (YouTube, Vimeo, Twitter, Soundcloud, direct MP4/M3U8...)"
              className="w-full bg-transparent text-sm sm:text-base text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 dark:placeholder:text-zinc-500 focus:outline-none"
              disabled={isLoading}
              autoFocus
            />

            {/* Clear Button */}
            {url && (
              <button
                type="button"
                onClick={() => setUrl('')}
                disabled={isLoading}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                title="Clear input"
              >
                <X size={16} />
              </button>
            )}

            {/* Paste from Clipboard */}
            {!url && (
              <button
                type="button"
                onClick={handlePaste}
                className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 bg-zinc-100 dark:bg-zinc-800/80 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
                title="Paste from clipboard"
              >
                <ClipboardText size={15} />
                <span>{pasteNotice ? 'Pasted!' : 'Paste'}</span>
              </button>
            )}
          </div>

          {/* Analyze Action Button */}
          <button
            type="submit"
            disabled={!url.trim() || isLoading}
            className="flex items-center justify-center gap-2 px-7 py-3 rounded-xl text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-brand-600 transition shadow-sm shadow-brand-500/25 shrink-0"
          >
            {isLoading ? (
              <>
                <CircleNotch size={18} className="animate-spin" />
                <span>Inspecting Media...</span>
              </>
            ) : (
              <>
                <MagnifyingGlass size={18} weight="bold" />
                <span>Analyze</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Feature capabilities & Sample Chips */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
        {/* Quick test chips */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="flex items-center gap-1 font-semibold text-zinc-600 dark:text-zinc-300 mr-1">
            <Sparkle size={13} className="text-amber-500" />
            <span>Test:</span>
          </span>
          {SAMPLE_URLS.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setUrl(sample.url);
                onAnalyze(sample.url);
              }}
              disabled={isLoading}
              className="px-2.5 py-1 rounded-lg bg-zinc-100/90 dark:bg-zinc-900/90 hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200/60 dark:border-zinc-800 transition disabled:opacity-50 text-[11px]"
            >
              {sample.label}
            </button>
          ))}
        </div>

        {/* Feature Badges */}
        <div className="hidden lg:flex items-center gap-3 text-[11px] font-mono text-zinc-400 dark:text-zinc-500">
          <span className="flex items-center gap-1">
            <Lightning size={12} className="text-amber-500" />
            <span>FAST EXTRACT</span>
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <FilmStrip size={12} className="text-brand-400" />
            <span>4K/8K STREAM</span>
          </span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <SpeakerHigh size={12} className="text-emerald-500" />
            <span>320K AUDIO</span>
          </span>
        </div>
      </div>
    </div>
  );
};
