import React, { useState } from 'react';
import {
  DownloadSimple,
  VideoCamera,
  MusicNotes,
  CheckCircle,
} from '@phosphor-icons/react';
import { AnalyzeResponse } from '../types';

interface FormatSelectorProps {
  media: AnalyzeResponse;
  onStartDownload: (params: {
    resolution: string;
    audio_only: boolean;
    audio_format: string;
    output_container: string;
  }) => void;
  isStarting: boolean;
}

export const FormatSelector: React.FC<FormatSelectorProps> = ({
  media,
  onStartDownload,
  isStarting,
}) => {
  const [isAudioOnly, setIsAudioOnly] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<string>('best');
  const [selectedAudioFormat, setSelectedAudioFormat] = useState<string>('mp3');
  const [selectedContainer, setSelectedContainer] = useState<string>('mp4');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onStartDownload({
      resolution: selectedResolution,
      audio_only: isAudioOnly,
      audio_format: selectedAudioFormat,
      output_container: isAudioOnly ? selectedAudioFormat : selectedContainer,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 shadow-sm space-y-5 transition-all"
    >
      <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
          Format & Quality Selection
        </h3>

        {/* Video vs Audio Toggle */}
        <div className="flex items-center p-1 bg-zinc-100 dark:bg-zinc-800 rounded-xl">
          <button
            type="button"
            onClick={() => setIsAudioOnly(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              !isAudioOnly
                ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            <VideoCamera size={14} />
            <span>Video</span>
          </button>
          <button
            type="button"
            onClick={() => setIsAudioOnly(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
              isAudioOnly
                ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-xs'
                : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
            }`}
          >
            <MusicNotes size={14} />
            <span>Audio Only</span>
          </button>
        </div>
      </div>

      {!isAudioOnly ? (
        /* Video Resolution Grid */
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
              Select Video Quality
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {media.video_options.map((opt) => {
                const isSelected = selectedResolution === opt.resolution;
                return (
                  <button
                    key={opt.resolution}
                    type="button"
                    onClick={() => setSelectedResolution(opt.resolution)}
                    className={`relative flex items-center justify-between p-3 rounded-xl border text-left transition ${
                      isSelected
                        ? 'border-brand-600 bg-brand-50/50 dark:bg-brand-950/30 text-brand-900 dark:text-brand-100 ring-2 ring-brand-500/20'
                        : 'border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 text-zinc-800 dark:text-zinc-200'
                    }`}
                  >
                    <div>
                      <p className="text-xs font-semibold">{opt.label}</p>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 uppercase">
                        {opt.resolution}
                      </p>
                    </div>
                    {isSelected && (
                      <CheckCircle
                        size={18}
                        weight="fill"
                        className="text-brand-600 dark:text-brand-400 shrink-0"
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Container format */}
          <div>
            <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
              Video Container
            </label>
            <div className="flex items-center gap-2">
              {['mp4', 'mkv', 'webm'].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setSelectedContainer(c)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold uppercase tracking-wider border transition ${
                    selectedContainer === c
                      ? 'bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 border-zinc-900 dark:border-zinc-100'
                      : 'border-zinc-200 dark:border-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                  }`}
                >
                  .{c}
                </button>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* Audio Format Options */
        <div className="space-y-4">
          <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
            Select Audio Format
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {media.audio_options.map((opt) => {
              const isSelected = selectedAudioFormat === opt.format;
              return (
                <button
                  key={opt.format}
                  type="button"
                  onClick={() => setSelectedAudioFormat(opt.format)}
                  className={`relative flex items-center justify-between p-3 rounded-xl border text-left transition ${
                    isSelected
                      ? 'border-brand-600 bg-brand-50/50 dark:bg-brand-950/30 text-brand-900 dark:text-brand-100 ring-2 ring-brand-500/20'
                      : 'border-zinc-200 dark:border-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 text-zinc-800 dark:text-zinc-200'
                  }`}
                >
                  <div>
                    <p className="text-xs font-semibold">{opt.label}</p>
                    <p className="text-[11px] text-zinc-500 dark:text-zinc-400 uppercase">
                      .{opt.format}
                    </p>
                  </div>
                  {isSelected && (
                    <CheckCircle
                      size={18}
                      weight="fill"
                      className="text-brand-600 dark:text-brand-400 shrink-0"
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Start Download Action */}
      <div className="pt-2">
        <button
          type="submit"
          disabled={isStarting}
          className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl text-sm font-semibold text-white bg-brand-600 hover:bg-brand-500 active:scale-[0.99] disabled:opacity-50 transition shadow-sm shadow-brand-500/20"
        >
          <DownloadSimple size={20} weight="bold" />
          <span>{isStarting ? 'Queuing Job...' : 'Start Download'}</span>
        </button>
      </div>
    </form>
  );
};
