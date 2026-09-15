import React, { useState, useMemo } from 'react';
import { PlaylistItem } from '../types';
import { PlaylistItemRow } from './PlaylistItemRow';
import { MagnifyingGlass, X } from '@phosphor-icons/react';

interface PlaylistItemListProps {
  entries: PlaylistItem[];
  selectedIndices: Set<number>;
  onToggleIndex: (index: number) => void;
}

export const PlaylistItemList: React.FC<PlaylistItemListProps> = ({
  entries,
  selectedIndices,
  onToggleIndex,
}) => {
  const [filterQuery, setFilterQuery] = useState('');

  const filteredEntries = useMemo(() => {
    if (!filterQuery.trim()) return entries;
    const q = filterQuery.toLowerCase();
    return entries.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        (item.uploader && item.uploader.toLowerCase().includes(q))
    );
  }, [entries, filterQuery]);

  return (
    <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 p-4 space-y-3 shadow-xs text-left">
      {/* Search and List Header */}
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          Playlist Contents ({filteredEntries.length})
        </h4>

        {/* Search input */}
        <div className="relative w-full max-w-xs">
          <MagnifyingGlass
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400"
          />
          <input
            type="text"
            placeholder="Filter playlist items..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="w-full pl-8 pr-7 py-1.5 rounded-lg text-xs bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          {filterQuery && (
            <button
              onClick={() => setFilterQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 p-0.5"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable Container */}
      <div className="max-h-[380px] overflow-y-auto space-y-2 pr-1">
        {filteredEntries.length === 0 ? (
          <div className="py-12 text-center text-zinc-400 text-xs">
            No items match &quot;{filterQuery}&quot;
          </div>
        ) : (
          filteredEntries.map((item) => (
            <PlaylistItemRow
              key={item.id || item.index}
              item={item}
              isSelected={selectedIndices.has(item.index)}
              onToggle={onToggleIndex}
            />
          ))
        )}
      </div>
    </div>
  );
};
