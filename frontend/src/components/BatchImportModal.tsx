import React, { useState } from 'react';
import {
  X,
  UploadSimple,
  ListPlus,
  CheckCircle,
  WarningCircle,
  ArrowRight,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import { BatchImportResponse, ProfileModel } from '../types';

interface BatchImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  profiles: ProfileModel[];
  onSuccess: () => void;
}

export const BatchImportModal: React.FC<BatchImportModalProps> = ({
  isOpen,
  onClose,
  profiles,
  onSuccess,
}) => {
  const [inputText, setInputText] = useState('');
  const [priority, setPriority] = useState<'HIGH' | 'NORMAL' | 'LOW'>('NORMAL');
  const [selectedProfile, setSelectedProfile] = useState<string>('recommended');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<BatchImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const extractUrls = (text: string): string[] => {
    return text
      .split(/[\r\n,]+/)
      .map((u) => u.trim())
      .filter((u) => u.startsWith('http://') || u.startsWith('https://'));
  };

  const parsedUrls = extractUrls(inputText);
  const uniqueUrls = Array.from(new Set(parsedUrls));
  const duplicateCount = parsedUrls.length - uniqueUrls.length;

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      if (content) {
        setInputText((prev) => (prev ? `${prev}\n${content}` : content));
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleSubmit = async () => {
    if (uniqueUrls.length === 0) {
      setError('Please provide at least one valid HTTP or HTTPS media URL.');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const resp = await api.queueBatch(uniqueUrls, priority, selectedProfile);
      setResult(resp);
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Failed to submit batch URLs.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetModal = () => {
    setInputText('');
    setResult(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92dvh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4 border-b border-zinc-100 dark:border-zinc-800 gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
              <ListPlus size={20} weight="bold" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm sm:text-base font-bold text-zinc-900 dark:text-zinc-100 truncate">
                Batch URL Import
              </h2>
              <p className="text-[11px] sm:text-xs text-zinc-500 dark:text-zinc-400 truncate">
                Queue multiple media downloads with automated deduplication
              </p>
            </div>
          </div>
          <button
            onClick={resetModal}
            className="p-2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition shrink-0 min-h-[36px] min-w-[36px] flex items-center justify-center"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800/60 rounded-xl text-xs text-purple-700 dark:text-purple-300 flex items-center gap-2">
              <WarningCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {!result ? (
            <>
              {/* Textarea */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">
                    Paste URLs (one per line)
                  </label>
                  <label className="cursor-pointer text-xs font-medium text-purple-600 dark:text-purple-400 hover:text-purple-700 flex items-center gap-1">
                    <UploadSimple size={14} />
                    <span>Upload .txt / .csv</span>
                    <input
                      type="file"
                      accept=".txt,.csv"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                </div>
                <textarea
                  rows={6}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=...&#10;https://soundcloud.com/...&#10;https://vimeo.com/..."
                  className="w-full px-3.5 py-2.5 text-xs font-mono bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-y"
                />
              </div>

              {/* Counters */}
              <div className="flex items-center gap-4 text-xs font-medium text-zinc-500 dark:text-zinc-400">
                <span>
                  Valid URLs detected:{' '}
                  <strong className="text-zinc-900 dark:text-zinc-100 font-mono">
                    {uniqueUrls.length}
                  </strong>
                </span>
                {duplicateCount > 0 && (
                  <span className="text-purple-600 dark:text-purple-400">
                    ({duplicateCount} duplicate{duplicateCount > 1 ? 's' : ''} filtered)
                  </span>
                )}
              </div>

              {/* Controls Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-zinc-100 dark:border-zinc-800">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Queue Priority
                  </label>
                  <div className="grid grid-cols-3 gap-1.5 p-1 bg-zinc-100 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl">
                    {(['LOW', 'NORMAL', 'HIGH'] as const).map((p) => (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPriority(p)}
                        className={`py-1.5 text-xs font-bold rounded-lg transition ${
                          priority === p
                            ? 'bg-purple-600 text-white shadow-purple-sm'
                            : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
                        }`}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Download Profile
                  </label>
                  <select
                    value={selectedProfile}
                    onChange={(e) => setSelectedProfile(e.target.value)}
                    className="w-full px-3 py-2 text-xs font-medium bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-800 dark:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  >
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} {p.badge ? `(${p.badge})` : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </>
          ) : (
            /* Results View */
            <div className="space-y-4">
              <div className="p-4 bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-800/60 rounded-xl">
                <div className="flex items-center gap-2 text-sm font-bold text-purple-700 dark:text-purple-300 mb-2">
                  <CheckCircle size={18} weight="fill" />
                  <span>Batch Queue Complete</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 bg-white dark:bg-zinc-900 rounded-lg border border-purple-100 dark:border-purple-900/40">
                    <span className="text-zinc-500">Accepted</span>
                    <p className="text-base font-bold text-purple-600 font-mono">
                      {result.total_accepted}
                    </p>
                  </div>
                  <div className="p-2 bg-white dark:bg-zinc-900 rounded-lg border border-purple-100 dark:border-purple-900/40">
                    <span className="text-zinc-500">Duplicates</span>
                    <p className="text-base font-bold text-zinc-600 dark:text-zinc-400 font-mono">
                      {result.duplicates_skipped}
                    </p>
                  </div>
                  <div className="p-2 bg-white dark:bg-zinc-900 rounded-lg border border-purple-100 dark:border-purple-900/40">
                    <span className="text-zinc-500">Invalid</span>
                    <p className="text-base font-bold text-zinc-600 dark:text-zinc-400 font-mono">
                      {result.invalid_urls}
                    </p>
                  </div>
                </div>
              </div>

              <div className="max-h-56 overflow-y-auto space-y-1.5">
                {result.items.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-xs flex items-center justify-between"
                  >
                    <span className="truncate max-w-[80%] font-mono text-zinc-700 dark:text-zinc-300">
                      {item.url}
                    </span>
                    {item.valid ? (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60">
                        QUEUED
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] font-medium rounded-md bg-zinc-200 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                        {item.duplicate ? 'DUPLICATE' : 'SKIPPED'}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 sm:px-6 py-3 sm:py-4 border-t border-zinc-100 dark:border-zinc-800 flex flex-col-reverse sm:flex-row justify-end items-stretch sm:items-center gap-2.5 bg-zinc-50/50 dark:bg-zinc-950/50">
          {!result ? (
            <>
              <button
                type="button"
                onClick={resetModal}
                className="w-full sm:w-auto px-4 py-2 text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100 transition min-h-[44px] flex items-center justify-center"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting || uniqueUrls.length === 0}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition disabled:opacity-50 min-h-[44px]"
              >
                {isSubmitting ? (
                  <span>Processing...</span>
                ) : (
                  <>
                    <span>Queue {uniqueUrls.length} Downloads</span>
                    <ArrowRight size={14} weight="bold" />
                  </>
                )}
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={resetModal}
              className="w-full sm:w-auto px-5 py-2.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition min-h-[44px]"
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
