import React from 'react';
import {
  X,
  Trash,
  DownloadSimple,
  ClockCounterClockwise,
  CheckCircle,
  XCircle,
  CircleNotch,
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
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs transition-opacity">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 h-full shadow-2xl border-l border-zinc-200 dark:border-zinc-800 flex flex-col animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-2">
            <ClockCounterClockwise size={20} className="text-brand-500" />
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-sm sm:text-base">
              Download History
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
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
              <ClockCounterClockwise size={40} className="mb-2 stroke-1 opacity-40" />
              <p className="text-sm font-medium">No downloads yet</p>
              <p className="text-xs text-zinc-500 max-w-xs mt-1">
                Completed and active media downloads will appear here.
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
                  className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200/80 dark:border-zinc-800 space-y-2 text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p
                      className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 line-clamp-1"
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

                  <div className="flex items-center justify-between text-[11px] text-zinc-500 dark:text-zinc-400">
                    <div className="flex items-center gap-1.5">
                      {isCompleted && (
                        <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                          <CheckCircle size={13} weight="fill" />
                          <span>{job.output_filesize_formatted || 'Completed'}</span>
                        </span>
                      )}
                      {isFailed && (
                        <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400 font-medium">
                          <XCircle size={13} weight="fill" />
                          <span>Failed</span>
                        </span>
                      )}
                      {isCancelled && (
                        <span className="text-zinc-400">Cancelled</span>
                      )}
                      {!isCompleted && !isFailed && !isCancelled && (
                        <span className="flex items-center gap-1 text-brand-600 dark:text-brand-400 font-medium">
                          <CircleNotch size={13} className="animate-spin" />
                          <span>{job.progress.toFixed(0)}%</span>
                        </span>
                      )}
                    </div>

                    {isCompleted && (
                      <a
                        href={job.download_url || `/api/files/${job.id}`}
                        download={job.output_filename || 'media'}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded bg-zinc-200 dark:bg-zinc-700 hover:bg-brand-600 hover:text-white dark:hover:bg-brand-600 text-zinc-800 dark:text-zinc-200 font-medium transition"
                      >
                        <DownloadSimple size={12} weight="bold" />
                        <span>Download</span>
                      </a>
                    )}
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
