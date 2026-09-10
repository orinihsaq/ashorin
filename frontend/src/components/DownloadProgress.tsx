import React, { useState } from 'react';
import {
  DownloadSimple,
  StopCircle,
  CheckCircle,
  XCircle,
  ArrowClockwise,
} from '@phosphor-icons/react';
import { JobResponse } from '../types';

interface DownloadProgressProps {
  job: JobResponse;
  onCancel: (jobId: string) => void;
  onReset: () => void;
}

export const DownloadProgress: React.FC<DownloadProgressProps> = ({
  job,
  onCancel,
  onReset,
}) => {
  const [isCancelling, setIsCancelling] = useState(false);

  const handleCancelClick = () => {
    if (confirm('Are you sure you want to cancel this download?')) {
      setIsCancelling(true);
      onCancel(job.id);
    }
  };

  const isCompleted = job.status === 'COMPLETED';
  const isFailed = job.status === 'FAILED';
  const isCancelled = job.status === 'CANCELLED';
  const isInProgress = !isCompleted && !isFailed && !isCancelled;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm space-y-5 transition-all">
      {/* Header: Title and Status Pill */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide uppercase ${
                isCompleted
                  ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-800'
                  : isFailed || isCancelled
                  ? 'bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-400 border border-rose-300 dark:border-rose-800'
                  : 'bg-brand-100 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-300 dark:border-brand-800 animate-pulse'
              }`}
            >
              {job.current_stage || job.status}
            </span>
          </div>
          <h3
            className="text-sm sm:text-base font-semibold text-zinc-900 dark:text-zinc-100 truncate"
            title={job.title || job.url}
          >
            {job.title || job.url}
          </h3>
        </div>

        {/* Action Controls */}
        <div className="shrink-0 flex items-center gap-2">
          {isInProgress && (
            <button
              type="button"
              onClick={handleCancelClick}
              disabled={isCancelling}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/50 border border-rose-200 dark:border-rose-800 transition"
            >
              <StopCircle size={16} />
              <span>{isCancelling ? 'Cancelling...' : 'Cancel'}</span>
            </button>
          )}

          {(isCompleted || isFailed || isCancelled) && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
            >
              <ArrowClockwise size={15} />
              <span>Download Another</span>
            </button>
          )}
        </div>
      </div>

      {/* In-Progress State: Progress Bar and Metrics */}
      {isInProgress && (
        <div className="space-y-3">
          <div className="w-full bg-zinc-100 dark:bg-zinc-800 h-3 rounded-full overflow-hidden p-0.5">
            <div
              className="bg-brand-600 h-full rounded-full transition-all duration-300 ease-out"
              style={{ width: `${Math.max(job.progress, 5)}%` }}
            />
          </div>

          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800/80">
              <span className="block text-zinc-400 text-[10px] uppercase font-semibold">
                Progress
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                {job.progress.toFixed(1)}%
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800/80">
              <span className="block text-zinc-400 text-[10px] uppercase font-semibold">
                Speed
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                {job.speed || 'Calculating...'}
              </span>
            </div>
            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800/80">
              <span className="block text-zinc-400 text-[10px] uppercase font-semibold">
                ETA
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                {job.eta || 'Calculating...'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Completed State: Success Banner & Download File Button */}
      {isCompleted && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50">
            <CheckCircle
              size={32}
              weight="fill"
              className="text-emerald-500 shrink-0"
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">
                Download and processing completed!
              </p>
              <div className="flex items-center gap-2 text-xs text-emerald-700 dark:text-emerald-400 mt-0.5">
                <span className="truncate max-w-[280px]">
                  {job.output_filename}
                </span>
                {job.output_filesize_formatted && (
                  <span>({job.output_filesize_formatted})</span>
                )}
              </div>
            </div>
          </div>

          <a
            href={job.download_url || `/api/files/${job.id}`}
            download={job.output_filename || 'media_file'}
            className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] transition shadow-sm shadow-emerald-500/20"
          >
            <DownloadSimple size={20} weight="bold" />
            <span>Save File to Device</span>
          </a>
        </div>
      )}

      {/* Failed State */}
      {isFailed && (
        <div className="p-4 rounded-xl bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/50 space-y-2">
          <div className="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-semibold text-sm">
            <XCircle size={20} weight="fill" />
            <span>Download Failed</span>
          </div>
          <p className="text-xs text-rose-600 dark:text-rose-400">
            {job.error_message || 'Something went wrong while processing the download.'}
          </p>
        </div>
      )}

      {/* Cancelled State */}
      {isCancelled && (
        <div className="p-4 rounded-xl bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400">
          This download was cancelled. Temporary files have been cleaned up.
        </div>
      )}
    </div>
  );
};
