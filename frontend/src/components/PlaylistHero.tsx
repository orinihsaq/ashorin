import React from 'react';
import { AnalyzeResponse } from '../types';
import {
  Playlist,
  User,
  ListBullets,
  CheckCircle,
  Broadcast,
} from '@phosphor-icons/react';

interface PlaylistHeroProps {
  media: AnalyzeResponse;
  playlistMode: 'all' | 'selected' | 'single';
  onChangeMode: (mode: 'all' | 'selected' | 'single') => void;
  selectedCount: number;
  onKeepSynced?: () => void;
}

export const PlaylistHero: React.FC<PlaylistHeroProps> = ({
  media,
  playlistMode,
  onChangeMode,
  selectedCount,
  onKeepSynced,
}) => {
  const totalItems = media.entries?.length || media.entry_count || 0;

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 shadow-sm space-y-4 text-left">
      {/* Top Media Header */}
      <div className="flex flex-col sm:flex-row gap-4 items-start">
        {/* Playlist Thumbnail Cover */}
        <div className="relative w-full sm:w-44 aspect-video rounded-xl overflow-hidden bg-zinc-100 dark:bg-zinc-800 shrink-0 border border-zinc-200/60 dark:border-zinc-800 shadow-xs">
          {media.thumbnail ? (
            <img
              src={media.thumbnail}
              alt={media.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-zinc-400">
              <Playlist size={32} className="text-brand-500" />
            </div>
          )}
          {/* Overlay Tag */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-transparent flex items-end p-2.5">
            <span className="flex items-center gap-1 text-[11px] font-bold font-mono text-white bg-brand-600/90 backdrop-blur-xs px-2 py-0.5 rounded-md">
              <Playlist size={13} weight="bold" />
              <span>{totalItems} VIDEOS</span>
            </span>
          </div>
        </div>

        {/* Title & Info */}
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase tracking-wider bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300">
              <span>Playlist Archive</span>
            </div>

            {onKeepSynced && (
              <button
                type="button"
                onClick={onKeepSynced}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-950/90 hover:bg-purple-200 dark:hover:bg-purple-900 border border-purple-300 dark:border-purple-800 transition shadow-xs"
              >
                <Broadcast size={14} weight="bold" />
                <span>Keep Synced</span>
              </button>
            )}
          </div>

          <h3
            className="text-base sm:text-lg font-bold text-zinc-900 dark:text-zinc-50 leading-snug line-clamp-2"
            title={media.title}
          >
            {media.title}
          </h3>

          <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400">
            {media.uploader && (
              <span className="flex items-center gap-1 text-zinc-700 dark:text-zinc-300 font-medium">
                <User size={14} className="text-brand-500" />
                <span>{media.uploader}</span>
              </span>
            )}
            <span className="flex items-center gap-1 font-mono">
              <ListBullets size={14} className="text-brand-500" />
              <span>{totalItems} items indexed</span>
            </span>
          </div>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800">
        <div className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 mb-2">
          Extraction Scope:
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => onChangeMode('all')}
            className={`flex items-center justify-between p-3 rounded-xl border text-left transition ${
              playlistMode === 'all'
                ? 'bg-purple-50 dark:bg-purple-950/50 border-brand-500 text-brand-950 dark:text-purple-100 ring-1 ring-brand-500/20'
                : 'bg-zinc-50 dark:bg-zinc-950/40 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300'
            }`}
          >
            <div>
              <p className="text-xs font-bold">Entire Playlist</p>
              <p className="text-[10px] text-zinc-500 dark:text-zinc-400">
                All {totalItems} items
              </p>
            </div>
            {playlistMode === 'all' && (
              <CheckCircle size={18} weight="fill" className="text-brand-600 dark:text-brand-400 shrink-0" />
            )}
          </button>

          <button
            type="button"
            onClick={() => onChangeMode('selected')}
            className={`flex items-center justify-between p-3 rounded-xl border text-left transition ${
              playlistMode === 'selected'
                ? 'bg-purple-50 dark:bg-purple-950/50 border-brand-500 text-brand-950 dark:text-purple-100 ring-1 ring-brand-500/20'
                : 'bg-zinc-50 dark:bg-zinc-950/40 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300'
            }`}
          >
            <div>
              <p className="text-xs font-bold">Custom Selection</p>
              <p className="text-[10px] text-zinc-500 dark:text-zinc-400">
                {selectedCount} items chosen
              </p>
            </div>
            {playlistMode === 'selected' && (
              <CheckCircle size={18} weight="fill" className="text-brand-600 dark:text-brand-400 shrink-0" />
            )}
          </button>

          <button
            type="button"
            onClick={() => onChangeMode('single')}
            className={`flex items-center justify-between p-3 rounded-xl border text-left transition ${
              playlistMode === 'single'
                ? 'bg-purple-50 dark:bg-purple-950/50 border-brand-500 text-brand-950 dark:text-purple-100 ring-1 ring-brand-500/20'
                : 'bg-zinc-50 dark:bg-zinc-950/40 border-zinc-200 dark:border-zinc-800 text-zinc-700 dark:text-zinc-300 hover:border-zinc-300'
            }`}
          >
            <div>
              <p className="text-xs font-bold">First Video Only</p>
              <p className="text-[10px] text-zinc-500 dark:text-zinc-400">
                Skip rest of playlist
              </p>
            </div>
            {playlistMode === 'single' && (
              <CheckCircle size={18} weight="fill" className="text-brand-600 dark:text-brand-400 shrink-0" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
