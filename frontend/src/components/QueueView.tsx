import React, { useState } from 'react';
import {
  ArrowClockwise,
  ArrowUp,
  ArrowDown,
  Trash,
  Stop,
  Clock,
  ArrowsDownUp,
  Pause,
  Play,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import { JobResponse } from '../types';

interface QueueViewProps {
  jobs: JobResponse[];
  onRefresh: () => void;
}

export const QueueView: React.FC<QueueViewProps> = ({ jobs, onRefresh }) => {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handlePriorityChange = async (jobId: string, newPriority: string) => {
    setActionLoading(jobId);
    try {
      await api.setPriority(jobId, newPriority);
      onRefresh();
    } catch (err) {
      console.error('Failed to update priority', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetry = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      await api.retryJob(jobId);
      onRefresh();
    } catch (err) {
      console.error('Failed to retry job', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancel = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      await api.cancelJob(jobId);
      onRefresh();
    } catch (err) {
      console.error('Failed to cancel job', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePauseTorrent = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      await api.pauseTorrent(jobId);
      onRefresh();
    } catch (err) {
      console.error('Failed to pause torrent', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleResumeTorrent = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      await api.resumeTorrent(jobId);
      onRefresh();
    } catch (err) {
      console.error('Failed to resume torrent', err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleClearCompleted = async () => {
    try {
      await api.clearCompletedQueue();
      onRefresh();
    } catch (err) {
      console.error('Failed to clear completed jobs', err);
    }
  };


  const priorityOrder: Record<string, number> = { HIGH: 1, NORMAL: 2, LOW: 3 };
  const sortedQueue = [...jobs].sort((a, b) => {
    const pA = priorityOrder[a.priority || 'NORMAL'] || 2;
    const pB = priorityOrder[b.priority || 'NORMAL'] || 2;
    if (pA !== pB) return pA - pB;
    return (a.queue_order || 0) - (b.queue_order || 0);
  });

  return (
    <div className="w-full max-w-5xl mx-auto px-3 sm:px-6 py-6 space-y-6 min-w-0">
      {/* Top Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800 min-w-0">
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
            Download <span className="text-purple-600 dark:text-purple-400">Queue</span>
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            Active download pipeline, priority management, and scheduling
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleClearCompleted}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition"
          >
            <Trash size={14} />
            <span>Clear Finished</span>
          </button>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60 hover:bg-purple-100 dark:hover:bg-purple-900/60 transition"
          >
            <ArrowClockwise size={14} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Queue Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
          <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Active</span>
          <p className="text-lg font-mono font-bold text-purple-600 dark:text-purple-400">
            {jobs.filter((j) => j.status === 'DOWNLOADING' || j.status === 'PROCESSING').length}
          </p>
        </div>
        <div className="p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
          <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Waiting</span>
          <p className="text-lg font-mono font-bold text-zinc-800 dark:text-zinc-200">
            {jobs.filter((j) => j.status === 'QUEUED').length}
          </p>
        </div>
        <div className="p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
          <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">High Priority</span>
          <p className="text-lg font-mono font-bold text-purple-700 dark:text-purple-300">
            {jobs.filter((j) => j.priority === 'HIGH' && (j.status === 'QUEUED' || j.status === 'DOWNLOADING')).length}
          </p>
        </div>
        <div className="p-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
          <span className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Total Pipeline</span>
          <p className="text-lg font-mono font-bold text-zinc-600 dark:text-zinc-400">
            {jobs.length}
          </p>
        </div>
      </div>

      {/* Jobs List */}
      {sortedQueue.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-2xl bg-zinc-50/50 dark:bg-zinc-950/50">
          <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
            <ArrowsDownUp size={24} />
          </div>
          <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-200">Queue is empty</h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-sm mx-auto">
            Paste a media or playlist URL on the Home screen or use Batch Import to add downloads.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {sortedQueue.map((job) => {
            const isDownloading = job.status === 'DOWNLOADING' || job.status === 'PROCESSING';
            const isQueued = job.status === 'QUEUED';
            const isFailed = job.status === 'FAILED';
            const isCancelled = job.status === 'CANCELLED';

            return (
              <div
                key={job.id}
                className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm hover:border-purple-300 dark:hover:border-purple-900/60 transition"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    {/* Priority Badge */}
                    <div className="flex flex-col items-center gap-1">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded-md uppercase tracking-wider ${
                          job.priority === 'HIGH'
                            ? 'bg-purple-600 text-white shadow-purple-sm'
                            : job.priority === 'LOW'
                            ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400'
                            : 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60'
                        }`}
                      >
                        {job.priority || 'NORMAL'}
                      </span>
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 min-w-0">
                        <h4 className="text-xs sm:text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate">
                          {job.title || job.output_filename || job.url}
                        </h4>
                        {job.provider === 'torrent' ? (
                          <span className="px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-800 shrink-0">
                            TORRENT
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700 shrink-0">
                            YT-DLP
                          </span>
                        )}
                        {job.is_playlist && (
                          <span className="px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 shrink-0">
                            PLAYLIST
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                        {job.status === 'ACQUIRING_METADATA' || job.status === 'WAITING_FOR_METADATA' ? (
                          <span className="flex items-center gap-1 text-purple-600 dark:text-purple-400 font-semibold animate-pulse">
                            Acquiring metadata…
                          </span>
                        ) : job.status === 'PAUSED' ? (
                          <span className="flex items-center gap-1 text-zinc-500 dark:text-zinc-400 font-semibold">
                            Paused
                          </span>
                        ) : job.status === 'SEEDING' ? (
                          <span className="text-purple-600 dark:text-purple-400 font-semibold">
                            Seeding ({job.torrent_telemetry?.ratio ? job.torrent_telemetry.ratio.toFixed(2) : '0.00'}×)
                          </span>
                        ) : (
                          <span>{job.current_stage || job.status}</span>
                        )}

                        {job.provider === 'torrent' && job.status === 'DOWNLOADING' && (job.torrent_telemetry?.download_rate_human || job.torrent_telemetry?.download_speed) && (
                          <span className="text-purple-600 dark:text-purple-400 font-mono font-medium">
                            • {job.torrent_telemetry.download_rate_human || job.torrent_telemetry.download_speed}
                          </span>
                        )}
                        {job.provider === 'torrent' && (job.torrent_telemetry?.peers !== undefined || job.torrent_telemetry?.num_peers !== undefined) && (
                          <span className="font-mono">
                            • {job.torrent_telemetry.peers ?? job.torrent_telemetry.num_peers} peers
                          </span>
                        )}
                        {job.provider !== 'torrent' && job.speed && <span>• {job.speed}</span>}
                        {job.eta && <span>• ETA {job.eta}</span>}
                        {job.scheduled_for && (
                          <span className="flex items-center gap-1 text-purple-600 dark:text-purple-400">
                            <Clock size={12} />
                            <span>Scheduled: {new Date(job.scheduled_for * 1000).toLocaleTimeString()}</span>
                          </span>
                        )}
                        {job.retry_count && job.retry_count > 0 ? (
                          <span className="text-purple-600 dark:text-purple-400">
                            • Retry {job.retry_count}/{job.max_retries}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    {/* Torrent Pause / Resume Controls */}
                    {job.provider === 'torrent' && (
                      (job.status === 'DOWNLOADING' || job.status === 'SEEDING') ? (
                        <button
                          onClick={() => handlePauseTorrent(job.id)}
                          disabled={actionLoading === job.id}
                          className="p-2 text-zinc-400 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/60 rounded-xl transition min-h-[38px] min-w-[38px] flex items-center justify-center border border-zinc-200 dark:border-zinc-800"
                          title="Pause Torrent"
                          aria-label="Pause Torrent"
                        >
                          <Pause size={16} />
                        </button>
                      ) : job.status === 'PAUSED' ? (
                        <button
                          onClick={() => handleResumeTorrent(job.id)}
                          disabled={actionLoading === job.id}
                          className="p-2 text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/60 rounded-xl transition min-h-[38px] min-w-[38px] flex items-center justify-center border border-purple-300 dark:border-purple-800"
                          title="Resume Torrent"
                          aria-label="Resume Torrent"
                        >
                          <Play size={16} weight="fill" />
                        </button>
                      ) : null
                    )}

                    {/* Priority buttons */}
                    {isQueued && (
                      <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-950 p-1 rounded-lg border border-zinc-200 dark:border-zinc-800">
                        <button
                          onClick={() => handlePriorityChange(job.id, 'HIGH')}
                          disabled={actionLoading === job.id || job.priority === 'HIGH'}
                          className="p-2 text-xs text-zinc-500 hover:text-purple-600 dark:hover:text-purple-400 disabled:opacity-30 min-h-[36px] min-w-[36px] flex items-center justify-center"
                          title="Set High Priority"
                          aria-label="Set High Priority"
                        >
                          <ArrowUp size={16} />
                        </button>
                        <button
                          onClick={() => handlePriorityChange(job.id, 'LOW')}
                          disabled={actionLoading === job.id || job.priority === 'LOW'}
                          className="p-2 text-xs text-zinc-500 hover:text-purple-600 dark:hover:text-purple-400 disabled:opacity-30 min-h-[36px] min-w-[36px] flex items-center justify-center"
                          title="Set Low Priority"
                          aria-label="Set Low Priority"
                        >
                          <ArrowDown size={16} />
                        </button>
                      </div>
                    )}

                    {/* Retry button */}
                    {(isFailed || isCancelled) && (
                      <button
                        onClick={() => handleRetry(job.id)}
                        disabled={actionLoading === job.id}
                        className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple-sm transition min-h-[38px]"
                      >
                        <ArrowClockwise size={14} />
                        <span>Retry</span>
                      </button>
                    )}

                    {/* Cancel button */}
                    {(isDownloading || isQueued) && (
                      <button
                        onClick={() => handleCancel(job.id)}
                        disabled={actionLoading === job.id}
                        className="p-2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl transition min-h-[38px] min-w-[38px] flex items-center justify-center"
                        title="Cancel job"
                        aria-label="Cancel job"
                      >
                        <Stop size={16} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress bar */}
                {(isDownloading || isQueued) && (
                  <div className="mt-3">
                    <div className="w-full h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-purple-800 to-purple-500 rounded-full transition-all duration-300"
                        style={{ width: `${Math.max(job.progress, isDownloading ? 5 : 0)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
