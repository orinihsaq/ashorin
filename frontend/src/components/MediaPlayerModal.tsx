import React from 'react';
import {
  X,
  DownloadSimple,
  Heart,
  ShieldCheck,
  Video,
  MusicNotes,
} from '@phosphor-icons/react';
import { MediaItem } from '../types';

interface MediaPlayerModalProps {
  item: MediaItem | null;
  onClose: () => void;
  onToggleFavorite: (id: string) => void;
  onToggleProtect: (id: string) => void;
}

export const MediaPlayerModal: React.FC<MediaPlayerModalProps> = ({
  item,
  onClose,
  onToggleFavorite,
  onToggleProtect,
}) => {
  if (!item) return null;

  const isAudio = [
    'mp3',
    'm4a',
    'wav',
    'flac',
    'opus',
    'aac',
    'ogg',
  ].includes((item.container || '').toLowerCase());

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/75 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92dvh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50">
          <div className="flex items-center gap-2.5 min-w-0 pr-2">
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
              {isAudio ? <MusicNotes size={18} weight="bold" /> : <Video size={18} weight="bold" />}
            </div>
            <div className="min-w-0">
              <h3 className="text-xs sm:text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate">
                {item.title}
              </h3>
              <p className="text-[10px] sm:text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                {item.uploader || 'Unknown uploader'} • {(item.container || 'mp4').toUpperCase()} •{' '}
                {item.filesize_formatted}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800 transition shrink-0 min-h-[36px] min-w-[36px] flex items-center justify-center"
            aria-label="Close player"
          >
            <X size={18} />
          </button>
        </div>

        {/* Media Player Area */}
        <div className="bg-black flex items-center justify-center min-h-[220px] sm:min-h-[260px] max-h-[50vh] sm:max-h-[60vh] overflow-hidden flex-1">
          {isAudio ? (
            <div className="w-full max-w-md p-6 sm:p-8 text-center space-y-4 sm:space-y-6">
              <div className="w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-2xl bg-gradient-to-br from-purple-800 to-purple-600 flex items-center justify-center text-white shadow-purple">
                <MusicNotes size={36} weight="fill" />
              </div>
              <audio
                controls
                autoPlay
                className="w-full accent-purple-600"
                src={item.stream_url}
              >
                Your browser does not support HTML5 audio streaming.
              </audio>
            </div>
          ) : (
            <video
              controls
              autoPlay
              playsInline
              className="w-full h-full max-h-[50vh] sm:max-h-[60vh] object-contain accent-purple-600"
              src={item.stream_url}
            >
              Your browser does not support HTML5 video streaming.
            </video>
          )}
        </div>

        {/* Footer Controls */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 px-4 sm:px-6 py-3 sm:py-4 border-t border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-900">
          <div className="flex items-center gap-2">
            <button
              onClick={() => onToggleFavorite(item.id)}
              className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border transition min-h-[44px] ${
                item.is_favorite
                  ? 'bg-purple-50 dark:bg-purple-950/80 text-purple-600 dark:text-purple-300 border-purple-300 dark:border-purple-800'
                  : 'bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700 hover:text-purple-600'
              }`}
            >
              <Heart size={15} weight={item.is_favorite ? 'fill' : 'regular'} />
              <span>{item.is_favorite ? 'Favorited' : 'Favorite'}</span>
            </button>

            <button
              onClick={() => onToggleProtect(item.id)}
              className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl border transition min-h-[44px] ${
                item.is_protected
                  ? 'bg-purple-50 dark:bg-purple-950/80 text-purple-600 dark:text-purple-300 border-purple-300 dark:border-purple-800'
                  : 'bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700 hover:text-purple-600'
              }`}
            >
              <ShieldCheck size={15} weight={item.is_protected ? 'fill' : 'regular'} />
              <span>{item.is_protected ? 'Protected' : 'Protect'}</span>
            </button>
          </div>

          <a
            href={item.download_url}
            download={item.filename}
            className="w-full sm:w-auto flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white shadow-purple transition min-h-[44px]"
          >
            <DownloadSimple size={15} weight="bold" />
            <span>Download File</span>
          </a>
        </div>
      </div>
    </div>
  );
};
