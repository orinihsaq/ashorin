import React, { useState } from 'react';
import {
  X,
  Cpu,
  ArrowsClockwise,
  HardDrives,
  ShieldCheck,
  FilmStrip,
  Database,
} from '@phosphor-icons/react';
import { SystemInfoResponse } from '../types';

interface SystemInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  systemInfo: SystemInfoResponse | null;
  onUpdateYtDlp: () => Promise<void>;
  isUpdating: boolean;
}

export const SystemInfoModal: React.FC<SystemInfoModalProps> = ({
  isOpen,
  onClose,
  systemInfo,
  onUpdateYtDlp,
  isUpdating,
}) => {
  const [updateMsg, setUpdateMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleUpdate = async () => {
    setUpdateMsg(null);
    try {
      await onUpdateYtDlp();
      setUpdateMsg('Engine update check finished.');
    } catch {
      setUpdateMsg('Engine update failed.');
    }
  };

  const storage = systemInfo?.storage_info;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Cpu size={22} className="text-brand-500" />
            <h3 className="font-bold text-zinc-900 dark:text-zinc-100 text-base">
              ashori<span className="text-brand-500">N</span> Engine Diagnostics
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4 text-xs">
          {/* Engine Status Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* yt-dlp Status */}
            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                  <ShieldCheck size={16} className="text-brand-500" />
                  <span>yt-dlp Core</span>
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                  ACTIVE
                </span>
              </div>
              <p className="text-zinc-500 dark:text-zinc-400">
                Installed: <span className="font-mono text-zinc-800 dark:text-zinc-200 font-bold">{systemInfo?.ytdlp_version || 'Detecting...'}</span>
              </p>
              {systemInfo?.latest_ytdlp_version && (
                <p className="text-zinc-500 dark:text-zinc-400">
                  Latest: <span className="font-mono text-zinc-800 dark:text-zinc-200 font-semibold">{systemInfo.latest_ytdlp_version}</span>
                </p>
              )}
            </div>

            {/* FFmpeg Status */}
            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                  <FilmStrip size={16} className="text-brand-500" />
                  <span>FFmpeg Muxer</span>
                </span>
                {systemInfo?.ffmpeg_available ? (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300">
                    READY
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
                    MISSING
                  </span>
                )}
              </div>
              <p className="text-zinc-500 dark:text-zinc-400">
                Version: <span className="font-mono text-zinc-800 dark:text-zinc-200 font-bold">{systemInfo?.ffmpeg_version || 'Not detected'}</span>
              </p>
              <p className="text-zinc-500 dark:text-zinc-400">
                Hardware Acceleration: <span className="text-zinc-700 dark:text-zinc-300 font-medium">Software / Container</span>
              </p>
            </div>
          </div>

          {/* Storage & Disk Usage Gauge */}
          {storage && (
            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
                  <HardDrives size={16} className="text-indigo-500" />
                  <span>Persistent Disk Storage (/data)</span>
                </span>
                <span className="font-mono text-zinc-600 dark:text-zinc-400 font-bold">
                  {storage.percent_used}% Used
                </span>
              </div>

              {/* Progress gauge bar */}
              <div className="w-full bg-zinc-200 dark:bg-zinc-800 h-2.5 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    storage.percent_used > 90
                      ? 'bg-rose-500'
                      : storage.percent_used > 75
                      ? 'bg-amber-500'
                      : 'bg-brand-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(2, storage.percent_used))}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-zinc-500 dark:text-zinc-400">
                <span>Free: {storage.free_formatted}</span>
                <span>Used: {storage.used_formatted}</span>
                <span>Total: {storage.total_formatted}</span>
              </div>
            </div>
          )}

          {/* System Environment & Policies Table */}
          <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-950/70 border border-zinc-200/80 dark:border-zinc-800 space-y-2">
            <h4 className="font-bold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5 text-xs">
              <Database size={15} className="text-brand-500" />
              <span>Container Runtime Limits & Retention</span>
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 font-mono text-[11px] pt-1">
              <div>
                <span className="text-zinc-400 block text-[10px] uppercase font-sans">Max Concurrency</span>
                <span className="text-zinc-800 dark:text-zinc-200 font-bold">{systemInfo?.max_concurrent_downloads} workers</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px] uppercase font-sans">Download Retention</span>
                <span className="text-zinc-800 dark:text-zinc-200 font-bold">{systemInfo?.download_retention ? `${Math.round(systemInfo.download_retention / 3600)} hrs` : 'Disabled'}</span>
              </div>
              <div>
                <span className="text-zinc-400 block text-[10px] uppercase font-sans">Max Size Cap</span>
                <span className="text-zinc-800 dark:text-zinc-200 font-bold">{systemInfo?.max_download_size || 'Unlimited'}</span>
              </div>
            </div>
          </div>

          {/* Update Action Button */}
          <div className="pt-1 flex flex-col sm:flex-row items-center justify-between gap-3">
            {updateMsg && (
              <p className="text-xs text-brand-600 dark:text-brand-400 font-medium">
                {updateMsg}
              </p>
            )}
            <button
              type="button"
              onClick={handleUpdate}
              disabled={isUpdating}
              className="ml-auto inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-zinc-900 dark:bg-zinc-100 dark:text-zinc-900 hover:bg-zinc-800 dark:hover:bg-white active:scale-95 transition disabled:opacity-50"
            >
              <ArrowsClockwise size={14} className={isUpdating ? 'animate-spin' : ''} />
              <span>{isUpdating ? 'Checking Updates...' : 'Check & Update yt-dlp'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
