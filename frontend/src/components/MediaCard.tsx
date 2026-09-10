import React from 'react';
import {
  User,
  Clock,
  ArrowSquareOut,
  FilmStrip,
  SpeakerHigh,
  ImageBroken,
} from '@phosphor-icons/react';
import { AnalyzeResponse } from '../types';

interface MediaCardProps {
  media: AnalyzeResponse;
}

export const MediaCard: React.FC<MediaCardProps> = ({ media }) => {
  const [imgError, setImgError] = React.useState(false);

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 sm:p-5 shadow-sm transition-all">
      <div className="flex flex-col sm:flex-row gap-4 sm:gap-5 items-start">
        {/* Thumbnail with duration badge */}
        <div className="relative w-full sm:w-56 aspect-video rounded-xl overflow-hidden bg-zinc-100 dark:bg-zinc-800 shrink-0 border border-zinc-200/60 dark:border-zinc-800/80">
          {media.thumbnail && !imgError ? (
            <img
              src={media.thumbnail}
              alt={media.title}
              onError={() => setImgError(true)}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-600 gap-1">
              <ImageBroken size={28} />
              <span className="text-xs">No preview</span>
            </div>
          )}

          {/* Duration overlay badge */}
          {media.duration_string && (
            <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/80 text-white text-[11px] font-medium tracking-wide backdrop-blur-xs flex items-center gap-1">
              <Clock size={12} />
              <span>{media.duration_string}</span>
            </div>
          )}
        </div>

        {/* Media Details */}
        <div className="flex-1 min-w-0 space-y-2.5">
          {/* Site and Status Chips */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-brand-50 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60">
              {media.extractor}
            </span>

            {media.video_available && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                <FilmStrip size={13} />
                <span>Video</span>
              </span>
            )}

            {media.audio_available && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700">
                <SpeakerHigh size={13} />
                <span>Audio</span>
              </span>
            )}
          </div>

          {/* Title */}
          <h2
            className="text-base sm:text-lg font-semibold text-zinc-900 dark:text-zinc-100 line-clamp-2 leading-snug"
            title={media.title}
          >
            {media.title}
          </h2>

          {/* Uploader and Source Link */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400 pt-0.5">
            {media.uploader && (
              <div className="flex items-center gap-1.5 font-medium text-zinc-700 dark:text-zinc-300">
                <User size={15} />
                <span className="truncate max-w-[200px]">{media.uploader}</span>
              </div>
            )}

            <a
              href={media.webpage_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 hover:text-brand-600 dark:hover:text-brand-400 hover:underline transition"
            >
              <span>Visit Source</span>
              <ArrowSquareOut size={13} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
