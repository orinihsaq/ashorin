import React, { useState } from 'react';
import {
  X,
  HardDrives,
  ArrowRight,
  Info,
  Sliders,
  FolderSimple,
} from '@phosphor-icons/react';
import { PreflightResponse } from '../types';

interface PreflightModalProps {
  isOpen: boolean;
  onClose: () => void;
  preflight: PreflightResponse | null;
  isLoading: boolean;
  onConfirmQueue: () => void;
}

export const PreflightModal: React.FC<PreflightModalProps> = ({
  isOpen,
  onClose,
  preflight,
  isLoading,
  onConfirmQueue,
}) => {
  const [filter, setFilter] = useState<'all' | 'new' | 'existing' | 'upgrade'>('all');
  const [showExplanations, setShowExplanations] = useState(false);

  if (!isOpen) return null;

  const filteredItems = preflight
    ? preflight.items.filter((item) => {
        if (filter === 'all') return true;
        return item.status === filter;
      })
    : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92dvh]">
        {/* Modal Header */}
        <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h2 className="text-base sm:text-lg font-black text-zinc-900 dark:text-zinc-100 tracking-tight flex items-center gap-2">
              <span>Download</span>
              <span className="text-purple-600 dark:text-purple-400">Preview</span>
              <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded-md bg-purple-50 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60">
                Preflight
              </span>
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 truncate max-w-md">
              {preflight ? preflight.title : 'Validating storage and collection differences...'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800 transition shrink-0 min-h-[36px] min-w-[36px] flex items-center justify-center"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {isLoading || !preflight ? (
          <div className="py-24 text-center text-xs text-zinc-500 dark:text-zinc-400 flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-purple-600 border-t-transparent animate-spin" />
            <span>Calculating storage footprint and checking local library...</span>
          </div>
        ) : (
          <div className="p-6 overflow-y-auto space-y-5 flex-1 text-xs">
            {/* KPI Metric Summary Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-3 bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200/80 dark:border-purple-800/50 rounded-2xl">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">New Items</span>
                <span className="text-lg font-black text-purple-600 dark:text-purple-400 font-mono mt-0.5 block">
                  {preflight.new_items_count}
                </span>
              </div>

              <div className="p-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Existing</span>
                <span className="text-lg font-black text-zinc-700 dark:text-zinc-300 font-mono mt-0.5 block">
                  {preflight.existing_items_count}
                </span>
              </div>

              <div className="p-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Upgrades</span>
                <span className="text-lg font-black text-purple-600 dark:text-purple-400 font-mono mt-0.5 block">
                  {preflight.upgrade_items_count}
                </span>
              </div>

              <div className="p-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Est. Size</span>
                <span className="text-lg font-black text-zinc-900 dark:text-zinc-100 font-mono mt-0.5 block truncate">
                  {preflight.estimated_total_formatted}
                </span>
              </div>
            </div>

            {/* Storage Check Card */}
            <div className="p-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl space-y-2">
              <div className="flex items-center justify-between font-semibold">
                <div className="flex items-center gap-2">
                  <HardDrives size={16} className="text-purple-600 dark:text-purple-400" />
                  <span>Storage Check</span>
                </div>
                <span
                  className={`font-mono font-bold text-[11px] px-2 py-0.5 rounded-md ${
                    preflight.storage_status === 'sufficient'
                      ? 'bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300'
                      : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300'
                  }`}
                >
                  {preflight.disk_free_formatted} Available
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
                {preflight.storage_message}
              </p>
            </div>

            {/* Resolved Configuration & Destination */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-zinc-600 dark:text-zinc-400">
              <div className="p-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center gap-2">
                <Sliders size={16} className="text-purple-600 shrink-0" />
                <span className="truncate">
                  Profile: <strong className="text-zinc-900 dark:text-zinc-100">{preflight.resolved_profile_name}</strong>
                  {preflight.resolved_recipe_name && ` (${preflight.resolved_recipe_name})`}
                </span>
              </div>
              <div className="p-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl flex items-center gap-2">
                <FolderSimple size={16} className="text-purple-600 shrink-0" />
                <span className="truncate font-mono text-[11px]">
                  {preflight.destination_folder}
                </span>
              </div>
            </div>

            {/* Explanations Banner */}
            {preflight.explanations.length > 0 && (
              <div className="p-3.5 bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200/80 dark:border-purple-800/50 rounded-2xl text-[11px] space-y-1">
                <button
                  type="button"
                  onClick={() => setShowExplanations(!showExplanations)}
                  className="flex items-center justify-between w-full font-bold text-purple-800 dark:text-purple-300"
                >
                  <span className="flex items-center gap-1.5">
                    <Info size={14} />
                    <span>Why are these skipped or upgraded?</span>
                  </span>
                  <span>{showExplanations ? '▲ Hide' : '▼ Details'}</span>
                </button>
                {showExplanations && (
                  <ul className="list-disc list-inside space-y-1 pt-2 text-zinc-600 dark:text-zinc-400">
                    {preflight.explanations.map((exp, idx) => (
                      <li key={idx}>{exp}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Items List Filter & Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-zinc-700 dark:text-zinc-300">
                  Item Analysis ({preflight.selected_items})
                </span>
                <div className="flex items-center gap-1">
                  {(['all', 'new', 'existing', 'upgrade'] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => setFilter(mode)}
                      className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase transition ${
                        filter === mode
                          ? 'bg-purple-600 text-white'
                          : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>

              <div className="max-h-48 overflow-y-auto border border-zinc-200 dark:border-zinc-800 rounded-xl divide-y divide-zinc-100 dark:divide-zinc-800 bg-white dark:bg-zinc-900">
                {filteredItems.map((item) => (
                  <div key={item.index} className="p-2.5 flex items-center justify-between gap-3 text-[11px]">
                    <div className="min-w-0 flex-1 truncate">
                      <span className="font-mono text-zinc-400 mr-2">#{item.index}</span>
                      <span className="font-medium text-zinc-800 dark:text-zinc-200">{item.title}</span>
                      {item.reason && (
                        <p className="text-[10px] text-zinc-400 truncate mt-0.5">{item.reason}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {item.estimated_bytes_formatted && (
                        <span className="font-mono text-zinc-400 text-[10px] hidden sm:inline">
                          ~{item.estimated_bytes_formatted}
                        </span>
                      )}
                      <span
                        className={`px-1.5 py-0.2 text-[9px] font-mono font-bold rounded uppercase ${
                          item.status === 'new'
                            ? 'bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300'
                            : item.status === 'upgrade'
                            ? 'bg-purple-600 text-white'
                            : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500'
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-zinc-200 dark:border-zinc-800 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-2 bg-zinc-50 dark:bg-zinc-950">
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-4 py-2.5 sm:py-2 text-xs font-semibold rounded-xl text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition min-h-[44px] flex items-center justify-center"
          >
            Cancel
          </button>

          <button
            onClick={() => {
              onConfirmQueue();
              onClose();
            }}
            disabled={isLoading || !preflight || preflight.new_items_count + preflight.upgrade_items_count === 0}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple-sm transition disabled:opacity-50 min-h-[44px]"
          >
            <span>Queue {preflight ? preflight.new_items_count + preflight.upgrade_items_count : 0} Items</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};
