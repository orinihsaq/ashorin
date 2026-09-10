import React from 'react';
import {
  X,
  Trash,
  DownloadSimple,
  ClockCounterClockwise,
  CheckCircle,
  XCircle,
  ArrowSquareOut,
} from '@phosphor-icons/react';
import { JobResponse } from '../types';

interface JobHistoryProps {
  isOpen: boolean;
  onClose: () => void;
  jobs: JobResponse[];
  onDeleteJob: (jobId: string) => void;
}

export const JobHistory: React.FC<JobHistoryProps> = ({
  isOpen,
  onClose,
  jobs,
  onDeleteJob,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-xs transition-opacity animate-in fade-in duration-200">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 h-full shadow-2xl border-l border-zinc-200 dark:border-zinc-800 flex flex-col animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-2">
            <ClockCounterClockwise size={20} className="text-brand-500" />
            <h3 className="font-bold text-zinc-900 dark:text-zinc-100 text-base">
              ashori<span className="text-brand-500">N</span> History
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 font-mono font-bold text-zinc-600 dark:text-zinc-400">
              {jobs.length}
            </span>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
            aria-label="Close History"
          >
            <X size={18} />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {jobs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-zinc-400">
              <ClockCounterClockwise size={44} className="mb-2 stroke-1 opacity-40 text-brand-500" />
              <p className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
                No extractions recorded yet
              </p>
              <p className="text-xs text-zinc-500 max-w-xs mt-1">
                Completed and active media downloads will be cataloged here.
              </p>
            </div>
          ) : (
            jobs.map((job) => {
              const isCompleted = job.status === 'COMPLETED';
              const isFailed = job.status === 'FAILED';
              const isCancelled = job.status === 'CANCELLED';

              return (
                <div
                  key={job.id}
                  className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800 space-y-2 text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className="text-xs font-bold text-zinc-900 dark:text-zinc-100 line-clamp-1"
                      title={job.title || job.url}
                    >
                      {job.title || job.url}
                    </p>
                    <button
                      onClick={() => onDeleteJob(job.id)}
                      className="text-zinc-400 hover:text-rose-500 transition p-1"
                      title="Delete record"
                    >
                      <Trash size={14} />
                    </button>
                  </div>

                  {job.config_summary && (
                    <p className="text-[10px] font-mono text-brand-600 dark:text-brand-400 truncate">
                      {job.config_summary}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-zinc-500 dark:text-zinc-400 pt-0.5">
                    <div className="flex items-center gap-1.5">
                      {isCompleted && (
                        <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold font-mono">
                          <CheckCircle size={13} weight="fill" />
                          <span>{job.output_filesize_formatted || 'Done'}</span>
                        </span>
                      )}
                      {isFailed && (
                        <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold">
                          <XCircle size={13} weight="fill" />
                          <span>Failed</span>
                        </span>
                      )}
                      {isCancelled && (
                        <span className="text-zinc-400 italic">Cancelled</span>
                      )}
                      {!isCompleted && !isFailed && !isCancelled && (
                        <span className="text-brand-500 font-semibold font-mono">
                          {job.progress.toFixed(0)}%
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {isCompleted && (
                        <a
                          href={job.download_url || `/api/files/${job.id}`}
                          download={job.output_filename || 'media'}
                          className="flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-500 hover:underline"
                        >
                          <DownloadSimple size={13} weight="bold" />
                          <span>Save</span>
                        </a>
                      )}
                      <a
                        href={job.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
                        title="Open original webpage"
                      >
                        <ArrowSquareOut size={13} />
                      </a>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
