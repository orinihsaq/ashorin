import React, { useState } from 'react';
import {
  CheckSquare,
  Square,
  ArrowsLeftRight,
  SlidersHorizontal,
} from '@phosphor-icons/react';

interface PlaylistSelectionToolbarProps {
  totalCount: number;
  selectedCount: number;
  onSelectAll: () => void;
  onDeselectAll: () => void;
  onInvert: () => void;
  onApplyRange: (start: number, end: number) => void;
}

export const PlaylistSelectionToolbar: React.FC<PlaylistSelectionToolbarProps> = ({
  totalCount,
  selectedCount,
  onSelectAll,
  onDeselectAll,
  onInvert,
  onApplyRange,
}) => {
  const [rangeStart, setRangeStart] = useState<string>('1');
  const [rangeEnd, setRangeEnd] = useState<string>(String(Math.min(10, totalCount)));
  const [showRangeInput, setShowRangeInput] = useState(false);

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    const start = parseInt(rangeStart, 10);
    const end = parseInt(rangeEnd, 10);
    if (!isNaN(start) && !isNaN(end) && start > 0 && end >= start) {
      onApplyRange(start, Math.min(end, totalCount));
    }
  };

  return (
    <div className="p-3 sm:p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        {/* Counter Badge */}
        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold bg-purple-100/80 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-200/60 dark:border-purple-800/60">
            {selectedCount} of {totalCount} items selected
          </span>
          {selectedCount === 0 && (
            <span className="text-[11px] text-purple-600 dark:text-purple-400 font-medium">
              Select items to download
            </span>
          )}
        </div>

        {/* Quick Action Buttons */}
        <div className="grid grid-cols-2 sm:flex sm:items-center gap-1.5 w-full sm:w-auto">
          <button
            type="button"
            onClick={onSelectAll}
            className="flex items-center justify-center sm:justify-start gap-1 px-3 py-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-semibold text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-purple-400 hover:text-purple-600 dark:hover:text-purple-400 transition shadow-2xs min-h-[38px]"
            title="Select every video"
          >
            <CheckSquare size={14} weight="bold" className="text-purple-500" />
            <span>Select All</span>
          </button>

          <button
            type="button"
            onClick={onDeselectAll}
            className="flex items-center justify-center sm:justify-start gap-1 px-3 py-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-semibold text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-purple-400 hover:text-purple-600 dark:hover:text-purple-400 transition shadow-2xs min-h-[38px]"
            title="Deselect all videos"
          >
            <Square size={14} weight="bold" />
            <span>Clear</span>
          </button>

          <button
            type="button"
            onClick={onInvert}
            className="flex items-center justify-center sm:justify-start gap-1 px-3 py-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-semibold text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 hover:border-purple-400 hover:text-purple-600 dark:hover:text-purple-400 transition shadow-2xs min-h-[38px]"
            title="Invert current selection"
          >
            <ArrowsLeftRight size={14} weight="bold" />
            <span>Invert</span>
          </button>

          <button
            type="button"
            onClick={() => setShowRangeInput((prev) => !prev)}
            className={`flex items-center justify-center sm:justify-start gap-1 px-3 py-2 sm:px-2.5 sm:py-1.5 rounded-lg text-xs font-semibold border transition shadow-2xs min-h-[38px] ${
              showRangeInput
                ? 'bg-purple-600 text-white border-purple-600'
                : 'text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 hover:border-purple-400'
            }`}
            title="Toggle range selection"
          >
            <SlidersHorizontal size={14} weight="bold" />
            <span>Range</span>
          </button>
        </div>
      </div>

      {/* Expandable Range Selector */}
      {showRangeInput && (
        <form
          onSubmit={handleApply}
          className="flex flex-wrap items-center gap-2 pt-2 border-t border-zinc-200/60 dark:border-zinc-800 text-xs animate-in fade-in duration-150"
        >
          <span className="text-zinc-500 font-medium">Select Range from item:</span>
          <input
            type="number"
            min="1"
            max={totalCount}
            value={rangeStart}
            onChange={(e) => setRangeStart(e.target.value)}
            className="w-16 px-2 py-1.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono text-center focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <span className="text-zinc-500 font-medium">to</span>
          <input
            type="number"
            min="1"
            max={totalCount}
            value={rangeEnd}
            onChange={(e) => setRangeEnd(e.target.value)}
            className="w-16 px-2 py-1.5 rounded-md bg-white dark:bg-zinc-900 border border-zinc-300 dark:border-zinc-700 text-zinc-900 dark:text-zinc-100 font-mono text-center focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            type="submit"
            className="w-full sm:w-auto px-4 py-1.5 rounded-md font-bold text-white bg-brand-600 hover:bg-brand-500 transition shadow-2xs mt-1 sm:mt-0"
          >
            Apply Range
          </button>
        </form>
      )}
    </div>
  );
};
