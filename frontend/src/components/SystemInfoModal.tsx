import React, { useState } from 'react';
import {
  X,
  Cpu,
  ArrowsClockwise,
  HardDrives,
  ShieldCheck,
  FilmStrip,
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
      setUpdateMsg('Update check and sync completed.');
    } catch {
      setUpdateMsg('Update check failed.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-2.5">
            <Cpu size={22} className="text-brand-500" />
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-100 text-base">
              System & Media Engine Status
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Engine Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* yt-dlp status */}
            <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/80 dark:border-zinc-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <ShieldCheck size={16} className="text-brand-500" />
                  <span>yt-dlp Engine</span>
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300">
                  Active
                </span>
              </div>
              <p className="text-zinc-500 dark:text-zinc-400">
                Installed: <span className="font-mono text-zinc-800 dark:text-zinc-200 font-semibold">{systemInfo?.ytdlp_version || 'Unknown'}</span>
              </p>
              {systemInfo?.latest_ytdlp_version && (
                <p className="text-zinc-500 dark:text-zinc-400">
                  Latest: <span className="font-mono text-zinc-800 dark:text-zinc-200">{systemInfo.latest_ytdlp_version}</span>
                </p>
              )}
            </div>

            {/* FFmpeg status */}
            <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/80 dark:border-zinc-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-zinc-700 dark:text-zinc-300 flex items-center gap-1.5">
                  <FilmStrip size={16} className="text-brand-500" />
                  <span>FFmpeg Processing</span>
                </span>
                {systemInfo?.ffmpeg_available ? (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300">
                    Ready
                  </span>
                ) : (
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300">
                    Missing
                  </span>
                )}
              </div>
              <p className="text-zinc-500 dark:text-zinc-400">
                Version: <span className="font-mono text-zinc-800 dark:text-zinc-200">{systemInfo?.ffmpeg_version || 'Not detected'}</span>
              </p>
              <p className="text-zinc-500 dark:text-zinc-400">
                Audio/Video Merging: {systemInfo?.ffmpeg_available ? 'Supported' : 'Disabled'}
              </p>
            </div>
          </div>

          {/* Configuration Parameters */}
          <div className="p-3.5 rounded-xl bg-zinc-50 dark:bg-zinc-800/60 border border-zinc-200/80 dark:border-zinc-800 space-y-2.5">
            <h4 className="font-semibold text-zinc-800 dark:text-zinc-200 flex items-center gap-1.5">
              <HardDrives size={15} />
              <span>Runtime & Storage Policies</span>
            </h4>
            <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-zinc-600 dark:text-zinc-400">
              <div>
                <span className="block text-[10px] uppercase font-semibold text-zinc-400">Max Concurrent</span>
                <span className="font-medium text-zinc-900 dark:text-zinc-200">{systemInfo?.max_concurrent_downloads ?? 2} downloads</span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-semibold text-zinc-400">Max File Size</span>
                <span className="font-medium text-zinc-900 dark:text-zinc-200">{systemInfo?.max_download_size ?? '10G'}</span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-semibold text-zinc-400">Download Retention</span>
                <span className="font-medium text-zinc-900 dark:text-zinc-200">
                  {systemInfo?.download_retention ? `${Math.round(systemInfo.download_retention / 3600)} hours` : 'Unlimited'}
                </span>
              </div>
              <div>
                <span className="block text-[10px] uppercase font-semibold text-zinc-400">Temp Retention</span>
                <span className="font-medium text-zinc-900 dark:text-zinc-200">
                  {systemInfo?.temp_retention ? `${Math.round(systemInfo.temp_retention / 3600)} hours` : 'Immediate'}
                </span>
              </div>
            </div>
          </div>

          {/* Update Action Button */}
          <div className="pt-2 flex flex-col gap-2">
            <button
              onClick={handleUpdate}
              disabled={isUpdating}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-zinc-900 dark:text-zinc-100 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 active:scale-[0.99] disabled:opacity-50 transition border border-zinc-200 dark:border-zinc-700"
            >
              <ArrowsClockwise size={16} className={isUpdating ? 'animate-spin' : ''} />
              <span>{isUpdating ? 'Checking for updates...' : 'Check & Update yt-dlp Now'}</span>
            </button>
            {updateMsg && (
              <p className="text-center text-xs text-brand-600 dark:text-brand-400 font-medium">
                {updateMsg}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
