import React from 'react';
import { PlaylistItem } from '../types';
import { Check, VideoCamera, ArrowSquareOut } from '@phosphor-icons/react';

interface PlaylistItemRowProps {
  item: PlaylistItem;
  isSelected: boolean;
  onToggle: (index: number) => void;
}

export const PlaylistItemRow: React.FC<PlaylistItemRowProps> = ({
  item,
  isSelected,
  onToggle,
}) => {
  return (
    <div
      onClick={() => onToggle(item.index)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === ' ' || e.key === 'Enter') {
          e.preventDefault();
          onToggle(item.index);
        }
      }}
      className={`group flex items-center gap-3 p-2.5 sm:p-3 rounded-xl border transition cursor-pointer select-none text-left ${
        isSelected
          ? 'bg-purple-50/70 dark:bg-purple-950/40 border-brand-400/80 dark:border-brand-600/70 shadow-xs ring-1 ring-brand-500/20'
          : 'bg-white dark:bg-zinc-900/60 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700 hover:bg-zinc-50 dark:hover:bg-zinc-800/40'
      }`}
    >
      {/* Checkbox */}
      <div
        className={`w-5 h-5 rounded-md border flex items-center justify-center transition shrink-0 ${
          isSelected
            ? 'bg-brand-600 border-brand-600 text-white shadow-xs'
            : 'border-zinc-300 dark:border-zinc-700 bg-white dark:bg-zinc-800 group-hover:border-brand-400'
        }`}
      >
        {isSelected && <Check size={13} weight="bold" />}
      </div>

      {/* Monospace Index Badge */}
      <span className="w-7 text-center shrink-0 font-mono text-[11px] font-bold text-zinc-400 dark:text-zinc-500">
        #{String(item.index).padStart(2, '0')}
      </span>

      {/* Thumbnail */}
      <div className="relative w-16 sm:w-20 aspect-video rounded-lg overflow-hidden bg-zinc-100 dark:bg-zinc-800 shrink-0 border border-zinc-200/60 dark:border-zinc-800">
        {item.thumbnail ? (
          <img
            src={item.thumbnail}
            alt={item.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-400">
            <VideoCamera size={18} />
          </div>
        )}
        {item.duration_string && (
          <span className="absolute bottom-1 right-1 px-1 py-0.2 rounded bg-black/80 text-[9px] font-mono font-semibold text-white">
            {item.duration_string}
          </span>
        )}
      </div>

      {/* Title & Metadata */}
      <div className="flex-1 min-w-0 pr-1">
        <p
          className={`text-xs sm:text-sm font-semibold truncate transition ${
            isSelected
              ? 'text-purple-950 dark:text-purple-100'
              : 'text-zinc-900 dark:text-zinc-100'
          }`}
          title={item.title}
        >
          {item.title}
        </p>
        <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate mt-0.5">
          {item.uploader || 'Unknown Creator'}
        </p>
      </div>

      {/* External Link */}
      {item.url && (
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="p-1.5 rounded-lg text-zinc-400 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition shrink-0 opacity-60 sm:opacity-0 group-hover:opacity-100 min-h-[32px] min-w-[32px] flex items-center justify-center"
          title="Open source video"
          aria-label="Open source video"
        >
          <ArrowSquareOut size={15} />
        </a>
      )}
    </div>
  );
};
