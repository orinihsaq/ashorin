import React, { useState } from 'react';
import {
  StopCircle,
  XCircle,
  ArrowClockwise,
  Cpu,
  CaretDown,
  CaretUp,
  CircleNotch,
  Check,
} from '@phosphor-icons/react';
import { JobResponse } from '../types';
import { CompletionPanel } from './CompletionPanel';

interface DownloadProgressProps {
  job: JobResponse;
  onCancel: (jobId: string) => void;
  onReset: () => void;
}

const STAGES = [
  { id: 'preparing', label: 'Preparing' },
  { id: 'extracting', label: 'Extracting' },
  { id: 'downloading', label: 'Downloading' },
  { id: 'merging', label: 'Merging' },
  { id: 'completed', label: 'Completed' },
];

export const DownloadProgress: React.FC<DownloadProgressProps> = ({
  job,
  onCancel,
  onReset,
}) => {
  const [isCancelling, setIsCancelling] = useState(false);
  const [showTechDetails, setShowTechDetails] = useState(false);

  const isCompleted = job.status === 'COMPLETED';
  const isFailed = job.status === 'FAILED';
  const isCancelled = job.status === 'CANCELLED';
  const isInProgress = !isCompleted && !isFailed && !isCancelled;

  // Determine stage index
  const getStageIndex = () => {
    if (isCompleted) return 4;
    const stage = (job.current_stage || '').toLowerCase();
    if (stage.includes('merg') || stage.includes('mux') || stage.includes('transcod') || job.status === 'PROCESSING') return 3;
    if (stage.includes('download') || job.status === 'DOWNLOADING') return 2;
    if (stage.includes('extract') || stage.includes('analyz') || job.status === 'ANALYZING') return 1;
    return 0; // preparing
  };

  const currentStageIndex = getStageIndex();

  const handleCancelClick = () => {
    if (confirm('Cancel this media extraction job? Temporary files will be cleaned.')) {
      setIsCancelling(true);
      onCancel(job.id);
    }
  };

  // If completed, delegate directly to the CompletionPanel
  if (isCompleted) {
    return <CompletionPanel job={job} onReset={onReset} />;
  }

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/90 rounded-2xl p-5 shadow-sm space-y-5 transition-all">
      {/* Header with Title and Cancel button */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase ${
                isFailed || isCancelled
                  ? 'bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-400 border border-rose-300 dark:border-rose-800'
                  : 'bg-brand-100 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-300 dark:border-brand-800 animate-pulse'
              }`}
            >
              {job.current_stage || job.status}
            </span>
          </div>

          <h3
            className="text-sm sm:text-base font-bold text-zinc-900 dark:text-zinc-100 truncate"
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
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/40 border border-rose-200 dark:border-rose-800/60 transition"
            >
              {isCancelling ? (
                <>
                  <CircleNotch size={14} className="animate-spin" />
                  <span>Cancelling...</span>
                </>
              ) : (
                <>
                  <StopCircle size={15} />
                  <span>Cancel</span>
                </>
              )}
            </button>
          )}

          {(isFailed || isCancelled) && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
            >
              <ArrowClockwise size={14} />
              <span>Retry / New</span>
            </button>
          )}
        </div>
      </div>

      {/* Stage Stepper Transitions */}
      {isInProgress && (
        <div className="py-2">
          <div className="flex items-center justify-between relative">
            <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-zinc-200 dark:bg-zinc-800 -translate-y-1/2 z-0" />
            <div
              className="absolute top-1/2 left-0 h-0.5 bg-brand-500 -translate-y-1/2 z-0 transition-all duration-500"
              style={{ width: `${(currentStageIndex / (STAGES.length - 1)) * 100}%` }}
            />

            {STAGES.map((stage, idx) => {
              const isPast = idx < currentStageIndex;
              const isCurrent = idx === currentStageIndex;

              return (
                <div key={stage.id} className="relative z-10 flex flex-col items-center">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold font-mono transition-all ${
                      isCurrent
                        ? 'bg-brand-600 text-white ring-4 ring-brand-500/20 scale-110'
                        : isPast
                        ? 'bg-emerald-500 text-white'
                        : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400'
                    }`}
                  >
                    {isPast ? <Check size={11} weight="bold" /> : idx + 1}
                  </div>
                  <span
                    className={`text-[10px] mt-1 font-semibold uppercase tracking-wider ${
                      isCurrent
                        ? 'text-brand-600 dark:text-brand-400'
                        : isPast
                        ? 'text-zinc-700 dark:text-zinc-300'
                        : 'text-zinc-400 dark:text-zinc-600'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* In-Progress Metrics & Progress Bar */}
      {isInProgress && (
        <div className="space-y-3 pt-1">
          <div className="w-full bg-zinc-100 dark:bg-zinc-950 h-3.5 rounded-full overflow-hidden p-0.5 border border-zinc-200/80 dark:border-zinc-800">
            <div
              className="bg-gradient-to-r from-brand-600 to-indigo-500 h-full rounded-full transition-all duration-300 ease-out shadow-xs shadow-brand-500/50"
              style={{ width: `${Math.max(job.progress, 4)}%` }}
            />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800">
              <span className="block text-zinc-400 text-[10px] uppercase font-sans font-semibold">
                Progress
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                {job.progress.toFixed(1)}%
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800">
              <span className="block text-zinc-400 text-[10px] uppercase font-sans font-semibold">
                Speed
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate block">
                {job.speed || 'Inspecting...'}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800">
              <span className="block text-zinc-400 text-[10px] uppercase font-sans font-semibold">
                ETA
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                {job.eta || '--:--'}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-100 dark:border-zinc-800">
              <span className="block text-zinc-400 text-[10px] uppercase font-sans font-semibold">
                Payload
              </span>
              <span className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate block">
                {job.downloaded_bytes
                  ? `${(job.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB`
                  : 'Streams...'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Failed State */}
      {isFailed && (
        <div className="p-4 rounded-xl bg-rose-50/80 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 space-y-2">
          <div className="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-bold text-sm">
            <XCircle size={20} weight="fill" />
            <span>Media Extraction Failed</span>
          </div>
          <p className="text-xs text-rose-600 dark:text-rose-400 font-mono">
            {job.error_message || 'An error occurred during yt-dlp execution.'}
          </p>
        </div>
      )}

      {/* Cancelled State */}
      {isCancelled && (
        <div className="p-4 rounded-xl bg-zinc-100 dark:bg-zinc-800/60 border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-400">
          Extraction was cancelled by user. Temporary worker files have been cleaned up.
        </div>
      )}

      {/* Expandable Technical Stats Accordion */}
      <div className="border-t border-zinc-100 dark:border-zinc-800/80 pt-2">
        <button
          type="button"
          onClick={() => setShowTechDetails((prev) => !prev)}
          className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 font-medium py-1 transition"
        >
          <Cpu size={14} className="text-brand-500" />
          <span>Technical Job Telemetry</span>
          {showTechDetails ? <CaretUp size={13} /> : <CaretDown size={13} />}
        </button>

        {showTechDetails && (
          <div className="p-3 mt-2 rounded-xl bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200/60 dark:border-zinc-800 font-mono text-[11px] space-y-1.5 text-zinc-600 dark:text-zinc-400 animate-in fade-in duration-150">
            <div>
              <span className="text-zinc-400">Job ID:</span>{' '}
              <span className="text-zinc-800 dark:text-zinc-200">{job.id}</span>
            </div>
            {job.config_summary && (
              <div>
                <span className="text-zinc-400">Config:</span>{' '}
                <span className="text-brand-600 dark:text-brand-400">{job.config_summary}</span>
              </div>
            )}
            <div>
              <span className="text-zinc-400">Stage:</span>{' '}
              <span className="text-zinc-800 dark:text-zinc-200">{job.current_stage || job.status}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
