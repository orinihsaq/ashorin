import React from 'react';
import { JobResponse } from '../types';
import {
  Playlist,
  SpinnerGap,
  StopCircle,
  WarningCircle,
  ArrowClockwise,
} from '@phosphor-icons/react';
import { CompletionPanel } from './CompletionPanel';

interface PlaylistProgressProps {
  job: JobResponse;
  onCancel: (jobId: string) => void;
  onReset: () => void;
}

export const PlaylistProgress: React.FC<PlaylistProgressProps> = ({
  job,
  onCancel,
  onReset,
}) => {
  const isCompleted = job.status === 'COMPLETED';
  const isFailed = job.status === 'FAILED';
  const isCancelled = job.status === 'CANCELLED';
  const isActive = !isCompleted && !isFailed && !isCancelled;

  if (isCompleted) {
    return <CompletionPanel job={job} onReset={onReset} />;
  }

  const completedCount = job.completed_items || 0;
  const totalCount = job.total_items || 1;
  const currentIdx = job.current_item_index || Math.min(completedCount + 1, totalCount);
  const currentItemProgress = job.current_item_progress || 0;

  return (
    <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200/80 dark:border-zinc-800 shadow-sm space-y-5 text-left animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300">
              <Playlist size={18} weight="bold" />
            </div>
            <span className="text-[11px] font-bold font-mono uppercase tracking-wider text-purple-700 dark:text-purple-300">
              {isActive ? 'Extracting Playlist Archive' : isCancelled ? 'Extraction Cancelled' : 'Extraction Stopped'}
            </span>
          </div>

          <h3 className="text-base sm:text-lg font-bold text-zinc-900 dark:text-zinc-100 truncate">
            {job.playlist_title || job.title || 'Playlist Download'}
          </h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            {job.current_stage || 'Processing items...'}
          </p>
        </div>

        {/* Status Badge */}
        <div className="shrink-0">
          {isActive && (
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60">
              <SpinnerGap size={13} className="animate-spin text-purple-600 dark:text-purple-400" />
              <span>{job.progress.toFixed(0)}% Overall</span>
            </span>
          )}
          {isCancelled && (
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
              Cancelled
            </span>
          )}
          {isFailed && (
            <span className="flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
              <WarningCircle size={14} weight="fill" />
              <span>Failed</span>
            </span>
          )}
        </div>
      </div>

      {/* Overall Progress Gauge */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs font-semibold">
          <span className="text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5 font-mono">
            <span>Overall Playlist Progress</span>
            <span className="text-purple-600 dark:text-purple-400">({completedCount} / {totalCount} items)</span>
          </span>
          <span className="font-mono text-purple-700 dark:text-purple-300 font-bold">
            {job.progress.toFixed(1)}%
          </span>
        </div>

        <div className="h-3 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden p-0.5 border border-zinc-200/50 dark:border-zinc-700/50">
          <div
            className="h-full rounded-full bg-gradient-to-r from-purple-600 via-brand-500 to-purple-400 transition-all duration-300 shadow-xs shadow-purple-500/20"
            style={{ width: `${Math.min(100, Math.max(0, job.progress))}%` }}
          />
        </div>
      </div>

      {/* Current Active Item Card */}
      {isActive && (
        <div className="p-4 rounded-xl bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200/70 dark:border-purple-800/40 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-zinc-800 dark:text-zinc-200 truncate flex items-center gap-1.5">
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-200/80 dark:bg-brand-900 text-brand-900 dark:text-brand-200">
                Item #{currentIdx}
              </span>
              <span className="truncate">{job.current_item_title || `Video ${currentIdx}`}</span>
            </span>
            <span className="font-mono text-purple-700 dark:text-purple-300 font-semibold shrink-0">
              {currentItemProgress.toFixed(0)}%
            </span>
          </div>

          <div className="h-1.5 w-full bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-200"
              style={{ width: `${Math.min(100, Math.max(0, currentItemProgress))}%` }}
            />
          </div>

          {/* Metrics: Speed & ETA */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono text-zinc-500 dark:text-zinc-400 pt-0.5">
            <div className="flex items-center gap-3">
              <span>Speed: <strong className="text-zinc-800 dark:text-zinc-200">{job.speed || 'Calculating...'}</strong></span>
              <span>ETA: <strong className="text-zinc-800 dark:text-zinc-200">{job.eta || 'Calculating...'}</strong></span>
            </div>
            {(job.failed_items || 0) > 0 && (
              <span className="text-purple-600 dark:text-purple-400 font-semibold">
                {job.failed_items} skipped / unavailable
              </span>
            )}
          </div>
        </div>
      )}

      {/* Error Message if Failed */}
      {isFailed && job.error_message && (
        <div className="p-4 rounded-xl bg-purple-50 dark:bg-purple-950/50 border border-purple-200 dark:border-purple-800/60 text-xs text-purple-900 dark:text-purple-200">
          <p className="font-bold mb-1">Extraction Failure</p>
          <p className="font-mono text-purple-800 dark:text-purple-300">{job.error_message}</p>
        </div>
      )}

      {/* Footer Controls */}
      <div className="pt-2 flex items-center justify-between gap-3 border-t border-zinc-100 dark:border-zinc-800">
        <div className="text-[11px] text-zinc-500 dark:text-zinc-400">
          {isActive
            ? 'Completed files are preserved in folder even if interrupted.'
            : isCancelled
            ? `${completedCount} items preserved in downloads directory.`
            : ''}
        </div>

        <div className="flex items-center gap-2">
          {isActive && (
            <button
              type="button"
              onClick={() => onCancel(job.id)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-purple-800 dark:text-purple-200 bg-purple-100/80 dark:bg-purple-950/80 hover:bg-purple-200 dark:hover:bg-purple-900/80 transition shadow-2xs"
            >
              <StopCircle size={15} weight="bold" />
              <span>Cancel Download</span>
            </button>
          )}

          {(isCompleted || isFailed || isCancelled) && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-brand-600 hover:bg-brand-500 transition shadow-xs"
            >
              <ArrowClockwise size={15} weight="bold" />
              <span>New Extraction</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
