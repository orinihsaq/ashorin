import React, { useEffect, useState } from 'react';
import {
  MagnifyingGlass,
  Play,
  DownloadSimple,
  Heart,
  ShieldCheck,
  Trash,
  GridFour,
  ListDashes,
  HardDrives,
  Video,
  MusicNotes,
  Folder,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import { MediaItem, MediaStorageSummary } from '../types';
import { MediaPlayerModal } from './MediaPlayerModal';

export const LibraryView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'all' | 'video' | 'audio' | 'playlist'>('all');
  const [providerFilter, setProviderFilter] = useState<'all' | 'ytdlp' | 'torrent'>('all');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<MediaItem[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [storage, setStorage] = useState<MediaStorageSummary | null>(null);
  const [selectedMedia, setSelectedMedia] = useState<MediaItem | null>(null);

  const fetchLibrary = async () => {
    setLoading(true);
    try {
      const typeParam = activeTab === 'all' ? undefined : activeTab;
      const resp = await api.getLibrary({
        type: typeParam,
        provider: providerFilter === 'all' ? undefined : providerFilter,
        search: search.trim() || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page,
        page_size: 18,
      });
      setItems(resp.items);
      setTotalItems(resp.total);
      setTotalPages(resp.total_pages);
    } catch (err) {
      console.error('Failed to load media library', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchStorage = async () => {
    try {
      const s = await api.getStorageSummary();
      setStorage(s);
    } catch (err) {
      console.error('Failed to load storage summary', err);
    }
  };

  useEffect(() => {
    fetchLibrary();
  }, [activeTab, providerFilter, sortBy, sortOrder, page]);

  useEffect(() => {
    fetchStorage();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLibrary();
  };

  const handleToggleFavorite = async (id: string) => {
    try {
      const resp = await api.toggleFavorite(id);
      setItems((prev) =>
        prev.map((it) => (it.id === id ? { ...it, is_favorite: resp.is_favorite } : it))
      );
      if (selectedMedia && selectedMedia.id === id) {
        setSelectedMedia((prev) => (prev ? { ...prev, is_favorite: resp.is_favorite } : null));
      }
    } catch (err) {
      console.error('Failed to toggle favorite', err);
    }
  };

  const handleToggleProtect = async (id: string) => {
    try {
      const resp = await api.toggleProtect(id);
      setItems((prev) =>
        prev.map((it) => (it.id === id ? { ...it, is_protected: resp.is_protected } : it))
      );
      if (selectedMedia && selectedMedia.id === id) {
        setSelectedMedia((prev) => (prev ? { ...prev, is_protected: resp.is_protected } : null));
      }
    } catch (err) {
      console.error('Failed to toggle protect', err);
    }
  };

  const handleDelete = async (id: string, isProtected: boolean) => {
    if (isProtected) {
      alert('This media item is protected against deletion. Unprotect it before deleting.');
      return;
    }
    if (!confirm('Permanently delete this media file from disk?')) {
      return;
    }

    try {
      await api.deleteMediaItem(id);
      fetchLibrary();
      fetchStorage();
    } catch (err: any) {
      alert(err.message || 'Failed to delete media item.');
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-3 sm:px-6 py-6 space-y-6 min-w-0">
      {/* Header & Storage Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
            Media <span className="text-purple-600 dark:text-purple-400">Library</span>
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            Organized local archive with instant streaming and storage protection ({totalItems} items)
          </p>
        </div>

        {storage && (
          <div className="flex items-center gap-3 px-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm text-xs">
            <HardDrives size={20} className="text-purple-600 dark:text-purple-400 shrink-0" />
            <div>
              <div className="flex items-center gap-2 font-bold text-zinc-800 dark:text-zinc-200">
                <span>{storage.total_formatted} in archive</span>
                <span className="text-zinc-400">•</span>
                <span className="text-zinc-500 font-normal">{storage.disk_free_formatted} disk free</span>
              </div>
              <div className="text-[11px] text-zinc-500 flex gap-2">
                <span>{storage.videos_count} videos</span>
                <span>•</span>
                <span>{storage.audio_count} audio</span>
                <span>•</span>
                <span>{storage.playlists_count} playlists</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Filter & Search Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Type Tabs */}
        <div className="flex items-center p-1 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl w-full sm:w-auto overflow-x-auto">
          {[
            { id: 'all', label: 'All Media' },
            { id: 'video', label: 'Videos' },
            { id: 'audio', label: 'Audio' },
            { id: 'playlist', label: 'Playlists' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as any);
                setPage(1);
              }}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white shadow-purple-sm'
                  : 'text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Sort Controls */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-2 w-full sm:w-auto">
          <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-64">
            <MagnifyingGlass size={15} className="absolute left-3 top-2.5 text-zinc-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search library..."
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
            />
          </form>

          {/* Sort Select */}
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={(e) => {
              const [sb, so] = e.target.value.split(':');
              setSortBy(sb);
              setSortOrder(so);
              setPage(1);
            }}
            className="flex-1 sm:flex-initial min-w-0 px-2.5 py-1.5 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-700 dark:text-zinc-300 focus:outline-none"
          >
            <option value="created_at:desc">Newest First</option>
            <option value="created_at:asc">Oldest First</option>
            <option value="title:asc">Title (A-Z)</option>
            <option value="filesize:desc">Largest Size</option>
          </select>

          {/* Provider Filter Select */}
          <select
            value={providerFilter}
            onChange={(e) => {
              setProviderFilter(e.target.value as any);
              setPage(1);
            }}
            className="flex-1 sm:flex-initial min-w-0 px-2.5 py-1.5 text-xs bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-700 dark:text-zinc-300 focus:outline-none"
          >
            <option value="all">All Sources</option>
            <option value="ytdlp">yt-dlp Only</option>
            <option value="torrent">Torrent Only</option>
          </select>

          {/* View Mode Toggle */}
          <div className="hidden sm:flex items-center p-1 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-lg ${
                viewMode === 'grid'
                  ? 'bg-purple-600 text-white'
                  : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
              }`}
            >
              <GridFour size={16} />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-lg ${
                viewMode === 'list'
                  ? 'bg-purple-600 text-white'
                  : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
              }`}
            >
              <ListDashes size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* Media Items */}
      {loading ? (
        <div className="py-20 text-center text-xs text-zinc-500">Loading library...</div>
      ) : items.length === 0 ? (
        <div className="py-20 text-center border border-dashed border-zinc-200 dark:border-zinc-800 rounded-3xl bg-zinc-50/50 dark:bg-zinc-950/50">
          <div className="w-12 h-12 mx-auto mb-3 rounded-2xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center">
            <Folder size={24} />
          </div>
          <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-200">No media found</h3>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            {search ? 'Try clearing your search query.' : 'Downloaded media will automatically appear here.'}
          </p>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="group flex flex-col bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-sm hover:shadow-md hover:border-purple-300 dark:hover:border-purple-900/60 transition"
            >
              {/* Thumbnail / Header */}
              <div
                onClick={() => setSelectedMedia(item)}
                className="relative aspect-video bg-zinc-950 cursor-pointer overflow-hidden flex items-center justify-center"
              >
                {item.thumbnail_url ? (
                  <img
                    src={item.thumbnail_url}
                    alt={item.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center">
                    {item.container === 'mp3' ? <MusicNotes size={24} /> : <Video size={24} />}
                  </div>
                )}

                {/* Duration Badge */}
                {item.duration_string && (
                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 text-[10px] font-mono font-bold rounded bg-black/80 text-white">
                    {item.duration_string}
                  </span>
                )}

                {/* Play Hover Overlay */}
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <div className="w-10 h-10 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-purple">
                    <Play size={18} weight="fill" />
                  </div>
                </div>

                {/* Protection / Favorite / Provider Icons */}
                <div className="absolute top-2 left-2 flex items-center gap-1">
                  {item.source_provider === 'torrent' && (
                    <span className="px-1.5 py-0.5 rounded-md bg-purple-950/90 text-purple-300 border border-purple-800/80 font-mono text-[9px] font-bold uppercase tracking-wider" title="BitTorrent Swarm Source">
                      Torrent
                    </span>
                  )}
                  {item.is_protected && (
                    <span className="p-1 rounded-md bg-purple-950/80 text-purple-300 border border-purple-800/60" title="Protected from retention cleanup">
                      <ShieldCheck size={14} weight="fill" />
                    </span>
                  )}
                  {item.is_favorite && (
                    <span className="p-1 rounded-md bg-purple-950/80 text-purple-300 border border-purple-800/60" title="Favorited">
                      <Heart size={14} weight="fill" />
                    </span>
                  )}
                </div>
              </div>

              {/* Body */}
              <div className="p-3.5 flex-1 flex flex-col justify-between space-y-2">
                <div>
                  <h3
                    onClick={() => setSelectedMedia(item)}
                    className="text-xs sm:text-sm font-bold text-zinc-900 dark:text-zinc-100 line-clamp-2 hover:text-purple-600 dark:hover:text-purple-400 cursor-pointer"
                  >
                    {item.title}
                  </h3>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 truncate">
                    {item.uploader || 'Unknown'} • {(item.container || 'mp4').toUpperCase()} • {item.filesize_formatted}
                  </p>
                </div>

                {/* Action Bar */}
                <div className="flex items-center justify-between pt-2 border-t border-zinc-100 dark:border-zinc-800 text-xs">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleToggleFavorite(item.id)}
                      className={`p-1.5 rounded-lg transition ${
                        item.is_favorite
                          ? 'text-purple-600 dark:text-purple-400'
                          : 'text-zinc-400 hover:text-purple-600'
                      }`}
                      title="Toggle favorite"
                    >
                      <Heart size={16} weight={item.is_favorite ? 'fill' : 'regular'} />
                    </button>
                    <button
                      onClick={() => handleToggleProtect(item.id)}
                      className={`p-1.5 rounded-lg transition ${
                        item.is_protected
                          ? 'text-purple-600 dark:text-purple-400'
                          : 'text-zinc-400 hover:text-purple-600'
                      }`}
                      title="Toggle protection against deletion"
                    >
                      <ShieldCheck size={16} weight={item.is_protected ? 'fill' : 'regular'} />
                    </button>
                    <button
                      onClick={() => handleDelete(item.id, item.is_protected)}
                      className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg transition"
                      title="Delete file"
                    >
                      <Trash size={16} />
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => setSelectedMedia(item)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-800 dark:text-zinc-200 font-medium"
                    >
                      <Play size={12} weight="fill" />
                      <span>Play</span>
                    </button>
                    <a
                      href={item.download_url}
                      download={item.filename}
                      className="p-1.5 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900 transition"
                      title="Download file to browser"
                    >
                      <DownloadSimple size={15} weight="bold" />
                    </a>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* List View */
        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden divide-y divide-zinc-100 dark:divide-zinc-800">
          {items.map((item) => (
            <div
              key={item.id}
              className="p-3 sm:p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 hover:bg-zinc-50 dark:hover:bg-zinc-950/40 transition"
            >
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div
                  onClick={() => setSelectedMedia(item)}
                  className="w-12 h-12 rounded-xl bg-zinc-950 flex items-center justify-center cursor-pointer shrink-0 overflow-hidden"
                >
                  {item.thumbnail_url ? (
                    <img src={item.thumbnail_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <Video size={20} className="text-purple-400" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    {item.source_provider === 'torrent' && (
                      <span className="shrink-0 px-1.5 py-0.2 text-[9px] font-mono font-bold rounded bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-800 uppercase tracking-wider">
                        Torrent
                      </span>
                    )}
                    <h4
                      onClick={() => setSelectedMedia(item)}
                      className="text-xs sm:text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate cursor-pointer hover:text-purple-600"
                    >
                      {item.title}
                    </h4>
                  </div>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                    {item.uploader || 'Unknown'} • {(item.container || 'mp4').toUpperCase()} • {item.filesize_formatted}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 shrink-0 self-end sm:self-center">
                <button
                  onClick={() => handleToggleFavorite(item.id)}
                  className={`p-1.5 rounded-lg ${
                    item.is_favorite ? 'text-purple-600' : 'text-zinc-400 hover:text-purple-600'
                  }`}
                >
                  <Heart size={16} weight={item.is_favorite ? 'fill' : 'regular'} />
                </button>
                <button
                  onClick={() => handleToggleProtect(item.id)}
                  className={`p-1.5 rounded-lg ${
                    item.is_protected ? 'text-purple-600' : 'text-zinc-400 hover:text-purple-600'
                  }`}
                >
                  <ShieldCheck size={16} weight={item.is_protected ? 'fill' : 'regular'} />
                </button>
                <button
                  onClick={() => setSelectedMedia(item)}
                  className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60"
                >
                  Stream
                </button>
                <a
                  href={item.download_url}
                  download={item.filename}
                  className="p-1.5 rounded-lg bg-purple-600 text-white hover:bg-purple-700"
                >
                  <DownloadSimple size={15} weight="bold" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 disabled:opacity-40"
          >
            Previous
          </button>
          <span className="text-xs text-zinc-500 font-mono">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      )}

      {/* Media Player Modal */}
      <MediaPlayerModal
        item={selectedMedia}
        onClose={() => setSelectedMedia(null)}
        onToggleFavorite={handleToggleFavorite}
        onToggleProtect={handleToggleProtect}
      />
    </div>
  );
};
