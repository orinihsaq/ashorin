import React, { useEffect, useState } from 'react';
import {
  Broadcast,
  Plus,
  Play,
  Pause,
  ArrowClockwise,
  Trash,
  Clock,
  X,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import {
  ProfileModel,
  RecipeModel,
  WatcherCreateRequest,
  WatcherModel,
  WatcherRunModel,
} from '../types';

interface WatchersViewProps {
  initialUrl?: string;
  initialTitle?: string;
}

export const WatchersView: React.FC<WatchersViewProps> = ({ initialUrl, initialTitle }) => {
  const [watchers, setWatchers] = useState<WatcherModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [selectedWatcher, setSelectedWatcher] = useState<WatcherModel | null>(null);
  const [runs, setRuns] = useState<WatcherRunModel[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Create Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(!!initialUrl);
  const [name, setName] = useState(initialTitle || '');
  const [sourceUrl, setSourceUrl] = useState(initialUrl || '');
  const [schedule, setSchedule] = useState('every_6_hours');
  const [profileId, setProfileId] = useState('recommended');
  const [recipeId, setRecipeId] = useState<string>('');
  const [targetQuality, setTargetQuality] = useState('1080p');
  const [downloadNew, setDownloadNew] = useState(true);
  const [createError, setCreateError] = useState<string | null>(null);

  const [profiles, setProfiles] = useState<ProfileModel[]>([]);
  const [recipes, setRecipes] = useState<RecipeModel[]>([]);

  useEffect(() => {
    loadWatchers();
    loadMeta();
  }, []);

  useEffect(() => {
    if (initialUrl) {
      setSourceUrl(initialUrl);
      if (initialTitle) setName(initialTitle);
      setIsCreateOpen(true);
    }
  }, [initialUrl, initialTitle]);

  const loadWatchers = async () => {
    setLoading(true);
    try {
      const list = await api.getWatchers();
      setWatchers(list);
    } catch (err) {
      console.error('Failed to load watchers', err);
    } finally {
      setLoading(false);
    }
  };

  const loadMeta = async () => {
    try {
      const [profs, recs] = await Promise.all([api.getProfiles(), api.getRecipes()]);
      setProfiles(profs);
      setRecipes(recs);
    } catch (err) {
      console.error('Failed to load profiles/recipes', err);
    }
  };

  const handleCreateWatcher = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !sourceUrl.trim()) return;
    setCreateError(null);

    const payload: WatcherCreateRequest = {
      name: name.trim(),
      source_url: sourceUrl.trim(),
      schedule,
      profile_id: profileId,
      recipe_id: recipeId || undefined,
      target_quality: targetQuality,
      download_new: downloadNew,
    };

    try {
      await api.createWatcher(payload);
      setIsCreateOpen(false);
      setName('');
      setSourceUrl('');
      loadWatchers();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create collection watcher.');
    }
  };

  const handleSyncNow = async (watcherId: string) => {
    setSyncingId(watcherId);
    try {
      await api.syncWatcher(watcherId);
      loadWatchers();
    } catch (err) {
      console.error('Sync failed', err);
    } finally {
      setSyncingId(null);
    }
  };

  const handleTogglePause = async (watcher: WatcherModel) => {
    try {
      if (watcher.status === 'PAUSED') {
        await api.resumeWatcher(watcher.id);
      } else {
        await api.pauseWatcher(watcher.id);
      }
      loadWatchers();
    } catch (err) {
      console.error('Failed to toggle watcher state', err);
    }
  };

  const handleDeleteWatcher = async (id: string) => {
    if (!confirm('Permanently delete this collection watcher?')) return;
    try {
      await api.deleteWatcher(id);
      loadWatchers();
    } catch (err) {
      console.error('Failed to delete watcher', err);
    }
  };

  const handleOpenHistory = async (watcher: WatcherModel) => {
    setSelectedWatcher(watcher);
    setIsHistoryOpen(true);
    try {
      const runList = await api.getWatcherRuns(watcher.id);
      setRuns(runList);
    } catch (err) {
      console.error('Failed to load runs', err);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-3 sm:px-6 py-6 space-y-6 min-w-0">
      {/* Top Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
            Collection <span className="text-purple-600 dark:text-purple-400">Watchers</span>
          </h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            Automated monitoring for playlists, channels, and feeds with smart sync
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsCreateOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple-sm transition"
          >
            <Plus size={14} weight="bold" />
            <span>Add Watcher</span>
          </button>
        </div>
      </div>

      {/* Watchers List */}
      {loading ? (
        <div className="py-24 text-center text-xs text-zinc-500">Loading collection watchers...</div>
      ) : watchers.length === 0 ? (
        <div className="py-20 text-center space-y-3 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-8">
          <div className="w-12 h-12 rounded-2xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 mx-auto flex items-center justify-center">
            <Broadcast size={24} />
          </div>
          <h3 className="text-sm font-bold text-zinc-800 dark:text-zinc-200">No Collection Watchers Yet</h3>
          <p className="text-xs text-zinc-500 max-w-sm mx-auto">
            Analyze a playlist or channel URL, or click &ldquo;Add Watcher&rdquo; to monitor creators and sync new releases automatically.
          </p>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="px-4 py-2 text-xs font-bold rounded-xl bg-purple-600 text-white hover:bg-purple-700 transition"
          >
            Create First Watcher
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {watchers.map((watcher) => {
            const isSyncing = syncingId === watcher.id;
            const isPaused = watcher.status === 'PAUSED';

            return (
              <div
                key={watcher.id}
                className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm hover:border-purple-300 dark:hover:border-purple-900/60 transition space-y-4"
              >
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full shrink-0 ${
                          isPaused ? 'bg-zinc-400' : 'bg-purple-600 ring-2 ring-purple-400/30'
                        }`}
                      />
                      <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 truncate">
                        {watcher.name}
                      </h3>
                    </div>
                    <p className="text-[11px] text-zinc-500 font-mono truncate mt-0.5">
                      {watcher.source_url}
                    </p>
                  </div>

                  <span
                    className={`px-2 py-0.5 text-[10px] font-mono font-bold rounded-md uppercase shrink-0 ${
                      isPaused
                        ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500'
                        : 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60'
                    }`}
                  >
                    {watcher.status}
                  </span>
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-2 text-xs text-zinc-600 dark:text-zinc-400">
                  <div className="p-2.5 bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 rounded-xl">
                    <span className="text-[10px] text-zinc-400 uppercase block font-bold">Tracked Items</span>
                    <span className="text-base font-black font-mono text-zinc-900 dark:text-zinc-100">
                      {watcher.items_tracked}
                    </span>
                  </div>
                  <div className="p-2.5 bg-zinc-50 dark:bg-zinc-950 border border-zinc-100 dark:border-zinc-800 rounded-xl">
                    <span className="text-[10px] text-zinc-400 uppercase block font-bold">Downloaded</span>
                    <span className="text-base font-black font-mono text-purple-600 dark:text-purple-400">
                      {watcher.items_downloaded}
                    </span>
                  </div>
                </div>

                {/* Sync Summary */}
                {watcher.last_sync_result && (
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400 truncate">
                    Last: {watcher.last_sync_result}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-zinc-100 dark:border-zinc-800/80">
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleSyncNow(watcher.id)}
                      disabled={isSyncing}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple-sm transition disabled:opacity-50"
                    >
                      <ArrowClockwise size={13} className={isSyncing ? 'animate-spin' : ''} />
                      <span>{isSyncing ? 'Syncing...' : 'Sync Now'}</span>
                    </button>
                    <button
                      onClick={() => handleTogglePause(watcher)}
                      className="p-1.5 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                      title={isPaused ? 'Resume Sync' : 'Pause Watcher'}
                    >
                      {isPaused ? <Play size={15} /> : <Pause size={15} />}
                    </button>
                    <button
                      onClick={() => handleOpenHistory(watcher)}
                      className="p-1.5 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                      title="Sync History"
                    >
                      <Clock size={15} />
                    </button>
                  </div>

                  <button
                    onClick={() => handleDeleteWatcher(watcher.id)}
                    className="p-1.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                    title="Delete Watcher"
                  >
                    <Trash size={15} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Watcher Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl shadow-2xl p-4 sm:p-6 space-y-4 max-h-[92dvh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
              <h2 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                Keep Source <span className="text-purple-600">Synced</span>
              </h2>
              <button onClick={() => setIsCreateOpen(false)} className="text-zinc-400 hover:text-zinc-600 p-1.5 min-h-[36px] min-w-[36px] flex items-center justify-center">
                <X size={18} />
              </button>
            </div>

            {createError && (
              <div className="p-3 bg-purple-50 dark:bg-purple-950/40 border border-purple-200 rounded-xl text-xs text-purple-800 dark:text-purple-200">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateWatcher} className="space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Collection Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Python Tutorials, Music Playlist"
                  className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                />
              </div>

              <div>
                <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                  Source URL (Playlist or Channel)
                </label>
                <input
                  type="url"
                  required
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  placeholder="https://www.youtube.com/playlist?list=..."
                  className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 font-mono text-[11px] focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Check Interval
                  </label>
                  <select
                    value={schedule}
                    onChange={(e) => setSchedule(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  >
                    <option value="hourly">Hourly</option>
                    <option value="every_3_hours">Every 3 Hours</option>
                    <option value="every_6_hours">Every 6 Hours</option>
                    <option value="every_12_hours">Every 12 Hours</option>
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Quality Target
                  </label>
                  <select
                    value={targetQuality}
                    onChange={(e) => setTargetQuality(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  >
                    <option value="1080p">1080p</option>
                    <option value="best">Best Available (4K/8K)</option>
                    <option value="720p">720p (Compact)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Recipe / Workflow
                  </label>
                  <select
                    value={recipeId}
                    onChange={(e) => setRecipeId(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  >
                    <option value="">Default Profile</option>
                    {recipes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                    Engine Profile
                  </label>
                  <select
                    value={profileId}
                    onChange={(e) => setProfileId(e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                  >
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="pt-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="dl_new"
                  checked={downloadNew}
                  onChange={(e) => setDownloadNew(e.target.checked)}
                  className="rounded border-zinc-300 text-purple-600 focus:ring-purple-500"
                />
                <label htmlFor="dl_new" className="font-semibold text-zinc-700 dark:text-zinc-300 cursor-pointer">
                  Automatically queue newly discovered items
                </label>
              </div>

              <div className="pt-4 border-t border-zinc-200 dark:border-zinc-800 flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 font-semibold text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 min-h-[40px] text-center"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white shadow-purple-sm transition min-h-[40px]"
                >
                  Start Watching
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Sync History Drawer/Modal */}
      {isHistoryOpen && selectedWatcher && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="relative w-full max-w-xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl shadow-2xl p-4 sm:p-6 space-y-4 max-h-[92dvh] flex flex-col">
            <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  Sync History: {selectedWatcher.name}
                </h3>
                <p className="text-xs text-zinc-500">Operation audit runs and discoveries</p>
              </div>
              <button onClick={() => setIsHistoryOpen(false)} className="text-zinc-400 hover:text-zinc-600 p-1.5 min-h-[36px] min-w-[36px] flex items-center justify-center">
                <X size={18} />
              </button>
            </div>

            <div className="overflow-y-auto space-y-2 flex-1 text-xs">
              {runs.length === 0 ? (
                <div className="py-12 text-center text-zinc-500">No sync runs recorded yet.</div>
              ) : (
                runs.map((r) => (
                  <div
                    key={r.id}
                    className="p-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] text-zinc-500">
                        {new Date(r.started_at * 1000).toLocaleString()}
                      </span>
                      <span
                        className={`px-1.5 py-0.2 text-[9px] font-mono font-bold rounded uppercase ${
                          r.status === 'COMPLETED'
                            ? 'bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300'
                            : 'bg-zinc-200 dark:bg-zinc-800 text-zinc-600'
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-zinc-600 dark:text-zinc-400 text-[11px]">
                      <span>Seen: {r.items_seen}</span>
                      <span>•</span>
                      <span className="font-bold text-purple-600">New: {r.new_items}</span>
                      <span>•</span>
                      <span>Queued: {r.queued}</span>
                      <span>•</span>
                      <span>Existing: {r.duplicates}</span>
                    </div>
                    {r.error && (
                      <p className="text-[10px] text-zinc-500 font-mono mt-1">{r.error}</p>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
              <button
                onClick={() => setIsHistoryOpen(false)}
                className="px-4 py-2 text-xs font-semibold rounded-xl bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
