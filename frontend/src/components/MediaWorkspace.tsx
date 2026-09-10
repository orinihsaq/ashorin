import React, { useState } from 'react';
import {
  Clock,
  ArrowSquareOut,
  FilmStrip,
  SpeakerHigh,
  ImageBroken,
  CaretDown,
  CaretUp,
  Cpu,
  Eye,
  CalendarBlank,
  User,
  Check,
  Copy,
} from '@phosphor-icons/react';
import { AnalyzeResponse } from '../types';

interface MediaWorkspaceProps {
  media: AnalyzeResponse;
}

export const MediaWorkspace: React.FC<MediaWorkspaceProps> = ({ media }) => {
  const [imgError, setImgError] = useState(false);
  const [showTechSpecs, setShowTechSpecs] = useState(false);
  const [copiedTitle, setCopiedTitle] = useState(false);

  const handleCopyTitle = () => {
    navigator.clipboard.writeText(media.title);
    setCopiedTitle(true);
    setTimeout(() => setCopiedTitle(false), 2000);
  };

  const formatViews = (views?: number | null) => {
    if (!views) return null;
    if (views >= 1_000_000_000) return `${(views / 1_000_000_000).toFixed(1)}B`;
    if (views >= 1_000_000) return `${(views / 1_000_000).toFixed(1)}M`;
    if (views >= 1_000) return `${(views / 1_000).toFixed(1)}K`;
    return views.toLocaleString();
  };

  const formatUploadDate = (dateStr?: string | null) => {
    if (!dateStr) return null;
    // Format YYYYMMDD to YYYY-MM-DD if yt-dlp raw format
    if (/^\d{8}$/.test(dateStr)) {
      return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
    }
    return dateStr;
  };

  const isHighRes = media.video_options.some(
    (o) => o.resolution.includes('2160p') || o.resolution.includes('1440p') || o.resolution.includes('4k')
  );

  return (
    <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800/90 rounded-2xl p-5 shadow-sm transition-all space-y-4">
      {/* Top Media Summary Row */}
      <div className="flex flex-col sm:flex-row gap-4 sm:gap-5 items-start">
        {/* Thumbnail Preview with Duration & High-Res Badges */}
        <div className="relative w-full sm:w-60 aspect-video rounded-xl overflow-hidden bg-zinc-100 dark:bg-zinc-950 shrink-0 border border-zinc-200/80 dark:border-zinc-800/80 shadow-xs">
          {media.thumbnail && !imgError ? (
            <img
              src={media.thumbnail}
              alt={media.title}
              onError={() => setImgError(true)}
              className="w-full h-full object-cover transition-transform duration-500 hover:scale-105"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-600 gap-1.5">
              <ImageBroken size={32} />
              <span className="text-xs font-medium">No preview available</span>
            </div>
          )}

          {/* Duration overlay badge */}
          {media.duration_string && (
            <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-zinc-950/85 text-zinc-100 text-[11px] font-mono font-medium tracking-wide backdrop-blur-xs flex items-center gap-1 shadow-sm">
              <Clock size={12} />
              <span>{media.duration_string}</span>
            </div>
          )}

          {/* 4K/UHD badge */}
          {isHighRes && (
            <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-amber-500 text-zinc-950 font-black text-[10px] tracking-wider uppercase shadow-sm">
              4K UHD
            </div>
          )}
        </div>

        {/* Media Information */}
        <div className="flex-1 min-w-0 space-y-2.5">
          {/* Header tags */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold bg-brand-50 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60 font-mono">
              {media.extractor.toUpperCase()}
            </span>

            {media.video_available && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/60">
                <FilmStrip size={13} className="text-brand-500" />
                <span>Video Stream</span>
              </span>
            )}

            {media.audio_available && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-100 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700/60">
                <SpeakerHigh size={13} className="text-emerald-500" />
                <span>Audio Stream</span>
              </span>
            )}
          </div>

          {/* Media Title */}
          <div className="group/title flex items-start justify-between gap-2">
            <h2
              className="text-base sm:text-lg font-bold text-zinc-900 dark:text-zinc-50 leading-snug line-clamp-2"
              title={media.title}
            >
              {media.title}
            </h2>
            <button
              type="button"
              onClick={handleCopyTitle}
              className="opacity-60 hover:opacity-100 p-1 rounded-md text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition shrink-0"
              title="Copy title"
            >
              {copiedTitle ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} />}
            </button>
          </div>

          {/* Metadata Row: Uploader, Date, Views, Link */}
          <div className="flex flex-wrap items-center gap-3 sm:gap-4 text-xs text-zinc-500 dark:text-zinc-400 pt-1">
            {media.uploader && (
              <div className="flex items-center gap-1.5 font-medium text-zinc-800 dark:text-zinc-200">
                {media.uploader_avatar ? (
                  <img
                    src={media.uploader_avatar}
                    alt={media.uploader}
                    className="w-4 h-4 rounded-full object-cover"
                  />
                ) : (
                  <User size={15} className="text-brand-500" />
                )}
                <span className="truncate max-w-[180px]">{media.uploader}</span>
              </div>
            )}

            {media.upload_date && (
              <div className="flex items-center gap-1">
                <CalendarBlank size={14} />
                <span>{formatUploadDate(media.upload_date)}</span>
              </div>
            )}

            {media.view_count !== undefined && media.view_count !== null && (
              <div className="flex items-center gap-1">
                <Eye size={14} />
                <span>{formatViews(media.view_count)} views</span>
              </div>
            )}

            <a
              href={media.webpage_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-brand-600 dark:text-brand-400 hover:underline font-medium ml-auto"
            >
              <span>Source URL</span>
              <ArrowSquareOut size={13} />
            </a>
          </div>
        </div>
      </div>

      {/* Technical Specifications Accordion */}
      <div className="border-t border-zinc-100 dark:border-zinc-800/80 pt-3">
        <button
          type="button"
          onClick={() => setShowTechSpecs((prev) => !prev)}
          className="w-full flex items-center justify-between text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200 py-1 transition"
        >
          <span className="flex items-center gap-1.5">
            <Cpu size={15} className="text-brand-500" />
            <span>Technical Stream Specifications</span>
            {media.technical_summary?.format_count ? (
              <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-100 dark:bg-zinc-800 font-mono">
                {media.technical_summary.format_count} streams
              </span>
            ) : null}
          </span>
          {showTechSpecs ? <CaretUp size={15} /> : <CaretDown size={15} />}
        </button>

        {showTechSpecs && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-3 pt-3 border-t border-zinc-100 dark:border-zinc-800/60 font-mono text-[11px] animate-in fade-in duration-150">
            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/60 dark:border-zinc-800">
              <span className="block text-zinc-400 dark:text-zinc-500 text-[10px] uppercase font-sans font-semibold">
                Video Codec
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200 truncate block" title={media.technical_summary?.vcodec || 'None'}>
                {media.technical_summary?.vcodec || 'Auto / None'}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/60 dark:border-zinc-800">
              <span className="block text-zinc-400 dark:text-zinc-500 text-[10px] uppercase font-sans font-semibold">
                Audio Codec
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200 truncate block" title={media.technical_summary?.acodec || 'None'}>
                {media.technical_summary?.acodec || 'Auto / None'}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/60 dark:border-zinc-800">
              <span className="block text-zinc-400 dark:text-zinc-500 text-[10px] uppercase font-sans font-semibold">
                Max Framerate
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {media.technical_summary?.fps ? `${media.technical_summary.fps} FPS` : 'Standard'}
              </span>
            </div>

            <div className="p-2.5 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/60 dark:border-zinc-800">
              <span className="block text-zinc-400 dark:text-zinc-500 text-[10px] uppercase font-sans font-semibold">
                Bitrate (TBR)
              </span>
              <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                {media.technical_summary?.tbr ? `${Math.round(media.technical_summary.tbr)} kbps` : 'Variable'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
