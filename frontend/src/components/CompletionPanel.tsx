import React, { useState } from 'react';
import {
  CheckCircle,
  DownloadSimple,
  ArrowClockwise,
  Copy,
  Check,
  HardDrive,
  FileVideo,
} from '@phosphor-icons/react';
import { JobResponse } from '../types';

interface CompletionPanelProps {
  job: JobResponse;
  onReset: () => void;
}

export const CompletionPanel: React.FC<CompletionPanelProps> = ({ job, onReset }) => {
  const [copiedName, setCopiedName] = useState(false);

  const handleCopyName = () => {
    if (job.output_filename) {
      navigator.clipboard.writeText(job.output_filename);
      setCopiedName(true);
      setTimeout(() => setCopiedName(false), 2000);
    }
  };

  const downloadUrl = job.download_url || `/api/files/${job.id}`;

  return (
    <div className="bg-white dark:bg-zinc-900 border border-emerald-500/30 dark:border-emerald-500/20 rounded-2xl p-6 shadow-lg shadow-emerald-500/5 space-y-5 transition-all animate-in fade-in zoom-in-95 duration-300">
      {/* Success banner */}
      <div className="flex items-start gap-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
        <div className="p-2 rounded-xl bg-emerald-500 text-white shadow-md shadow-emerald-500/30 shrink-0">
          <CheckCircle size={28} weight="fill" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-base font-bold text-zinc-900 dark:text-zinc-50">
              Extraction Complete!
            </h4>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
              SUCCESS
            </span>
          </div>

          {/* Filename & size */}
          <div className="mt-2 p-2.5 rounded-lg bg-white/70 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0 font-mono text-xs text-zinc-800 dark:text-zinc-200">
              <FileVideo size={16} className="text-emerald-500 shrink-0" />
              <span className="truncate font-semibold" title={job.output_filename || 'media'}>
                {job.output_filename || 'media_file'}
              </span>
            </div>
            <button
              type="button"
              onClick={handleCopyName}
              className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded transition shrink-0"
              title="Copy filename"
            >
              {copiedName ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400 mt-2">
            {job.output_filesize_formatted && (
              <span className="font-semibold text-zinc-700 dark:text-zinc-300 font-mono">
                Size: {job.output_filesize_formatted}
              </span>
            )}
            <span>•</span>
            <span className="flex items-center gap-1">
              <HardDrive size={13} className="text-brand-500" />
              <span>Saved to persistent storage: <code className="font-mono text-zinc-600 dark:text-zinc-300 font-semibold">/data/downloads</code></span>
            </span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center gap-3 pt-1">
        <a
          href={downloadUrl}
          download={job.output_filename || 'media_file'}
          className="w-full sm:flex-1 flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-500 active:scale-[0.99] transition shadow-md shadow-emerald-600/25"
        >
          <DownloadSimple size={20} weight="bold" />
          <span>Download File to Device</span>
        </a>

        <button
          type="button"
          onClick={onReset}
          className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl text-sm font-semibold text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 transition"
        >
          <ArrowClockwise size={16} />
          <span>Extract Another</span>
        </button>
      </div>
    </div>
  );
};
