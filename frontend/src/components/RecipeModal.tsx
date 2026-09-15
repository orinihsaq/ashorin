import React, { useState, useEffect } from 'react';
import {
  X,
  CookingPot,
  Plus,
  Trash,
  Copy,
  Star,
  FilmStrip,
  MusicNotes,
  DeviceMobile,
  Broadcast,
  Check,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import { RecipeModel, ProfileModel } from '../types';

interface RecipeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectRecipe?: (recipe: RecipeModel) => void;
  selectedRecipeId?: string | null;
}

export const RecipeModal: React.FC<RecipeModalProps> = ({
  isOpen,
  onClose,
  onSelectRecipe,
  selectedRecipeId,
}) => {
  const [recipes, setRecipes] = useState<RecipeModel[]>([]);
  const [profiles, setProfiles] = useState<ProfileModel[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // New recipe form state
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newProfileId, setNewProfileId] = useState('');
  const [newPathPattern, setNewPathPattern] = useState('{title}/{title}.%(ext)s');
  const [newDupPolicy, setNewDupPolicy] = useState('skip');
  const [newQualityPolicy, setNewQualityPolicy] = useState('upgrade_if_better');
  const [newRetentionDays, setNewRetentionDays] = useState(0);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [rList, pList] = await Promise.all([
        api.getRecipes().catch(() => []),
        api.getProfiles().catch(() => []),
      ]);
      setRecipes(rList);
      setProfiles(pList);
      if (pList.length > 0 && !newProfileId) {
        setNewProfileId(pList[0].id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCreateRecipe = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setErrorMsg(null);
    try {
      await api.createRecipe({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        profile_id: newProfileId || 'recommended',
        storage_folder: newPathPattern.trim() || undefined,
        duplicate_policy: newDupPolicy,
        upgrade_policy: newQualityPolicy,
        retention_days: newRetentionDays,
      });
      setIsCreating(false);
      setNewName('');
      setNewDesc('');
      await loadData();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to create recipe');
    }
  };

  const handleCloneRecipe = async (recipe: RecipeModel) => {
    const cloneName = prompt('Enter name for cloned recipe:', `${recipe.name} (Copy)`);
    if (!cloneName) return;
    try {
      await api.cloneRecipe(recipe.id, cloneName);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Clone failed');
    }
  };

  const handleSetDefault = async (recipeId: string) => {
    try {
      await api.setDefaultRecipe(recipeId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to set default');
    }
  };

  const handleDeleteRecipe = async (recipeId: string) => {
    if (!confirm('Are you sure you want to delete this custom recipe?')) return;
    try {
      await api.deleteRecipe(recipeId);
      await loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete');
    }
  };

  const getRecipeIcon = (id: string) => {
    if (id.includes('music')) return MusicNotes;
    if (id.includes('mobile')) return DeviceMobile;
    if (id.includes('podcast')) return Broadcast;
    return FilmStrip;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2.5 sm:p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-3xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[92dvh]">
        {/* Header */}
        <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <span className="p-1.5 rounded-lg bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400 shrink-0">
              <CookingPot size={20} weight="fill" />
            </span>
            <div className="min-w-0">
              <h2 className="text-base sm:text-lg font-black text-zinc-900 dark:text-zinc-100 tracking-tight flex items-center gap-2">
                <span>Download</span>
                <span className="text-purple-600 dark:text-purple-400">Recipes</span>
                <span className="hidden xs:inline-flex px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded-md bg-purple-50 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60">
                  Workflows
                </span>
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 truncate">
                Automation pipelines bundling profiles, storage, and retention.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {!isCreating && (
              <button
                onClick={() => setIsCreating(true)}
                className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 transition shadow-xs min-h-[36px]"
              >
                <Plus size={14} weight="bold" />
                <span className="hidden xs:inline">New Recipe</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800 transition min-h-[36px] min-w-[36px] flex items-center justify-center"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-4 flex-1 text-xs">
          {errorMsg && (
            <div className="p-3 bg-purple-100 dark:bg-purple-950/60 border border-purple-300 dark:border-purple-800 text-purple-900 dark:text-purple-100 rounded-xl">
              {errorMsg}
            </div>
          )}

          {isCreating ? (
            /* Recipe Creation Form */
            <form onSubmit={handleCreateRecipe} className="space-y-4 p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200 dark:border-zinc-800">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider">
                  Create Custom Recipe
                </h3>
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200"
                >
                  Cancel
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Recipe Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 4K HDR Archive"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Associated Profile</label>
                  <select
                    value={newProfileId}
                    onChange={(e) => setNewProfileId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="">None (Custom Engine Params)</option>
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Description</label>
                <input
                  type="text"
                  placeholder="Optional brief description of what this recipe does"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Duplicate Policy</label>
                  <select
                    value={newDupPolicy}
                    onChange={(e) => setNewDupPolicy(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="skip">Skip if already downloaded</option>
                    <option value="overwrite">Overwrite existing</option>
                    <option value="allow">Allow duplicate file</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Quality Upgrade Policy</label>
                  <select
                    value={newQualityPolicy}
                    onChange={(e) => setNewQualityPolicy(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value="upgrade_if_better">Upgrade if higher res/fps</option>
                    <option value="ignore">Keep original quality</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Retention Period</label>
                  <select
                    value={newRetentionDays}
                    onChange={(e) => setNewRetentionDays(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  >
                    <option value={0}>Permanent (Never Auto-Delete)</option>
                    <option value={7}>7 Days</option>
                    <option value={14}>14 Days</option>
                    <option value={30}>30 Days</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-zinc-700 dark:text-zinc-300 font-bold mb-1">Storage Path Pattern</label>
                <input
                  type="text"
                  placeholder="{title}/{title}.%(ext)s"
                  value={newPathPattern}
                  onChange={(e) => setNewPathPattern(e.target.value)}
                  className="w-full px-3 py-2 font-mono text-[11px] rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="px-3 py-1.5 rounded-xl border border-zinc-200 dark:border-zinc-700 text-zinc-600 dark:text-zinc-400 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-xl bg-purple-600 text-white font-bold hover:bg-purple-700 transition"
                >
                  Save Recipe
                </button>
              </div>
            </form>
          ) : null}

          {/* Recipes Listing */}
          {isLoading ? (
            <div className="py-12 text-center text-zinc-500">
              <div className="w-6 h-6 rounded-full border-2 border-purple-600 border-t-transparent animate-spin mx-auto mb-2" />
              Loading recipes...
            </div>
          ) : (
            <div className="space-y-3">
              {recipes.map((r) => {
                const Icon = getRecipeIcon(r.id);
                const isSelected = selectedRecipeId === r.id;

                return (
                  <div
                    key={r.id}
                    className={`p-4 rounded-2xl border transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                      isSelected
                        ? 'border-purple-600 bg-purple-50/40 dark:bg-purple-950/20 shadow-xs'
                        : 'border-zinc-200 dark:border-zinc-800 hover:border-purple-300 dark:hover:border-purple-800/60 bg-white dark:bg-zinc-900'
                    }`}
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="p-2.5 rounded-xl bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400 shrink-0">
                        <Icon size={20} weight="bold" />
                      </div>

                      <div className="space-y-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h4 className="font-bold text-sm text-zinc-900 dark:text-zinc-100">
                            {r.name}
                          </h4>
                          {r.is_default && (
                            <span className="px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded-md bg-purple-600 text-white">
                              Default
                            </span>
                          )}
                          {r.is_builtin && (
                            <span className="px-2 py-0.5 text-[9px] font-mono font-bold uppercase rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-300">
                              Built-in
                            </span>
                          )}
                        </div>

                        {r.description && (
                          <p className="text-zinc-500 dark:text-zinc-400 text-xs">
                            {r.description}
                          </p>
                        )}

                        {/* Badges / summary */}
                        <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[10px] font-mono text-zinc-500 dark:text-zinc-400">
                          <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                            dup: {r.duplicate_policy}
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                            upgrade: {r.upgrade_policy}
                          </span>
                          <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800">
                            retention: {r.retention_days ? `${r.retention_days}d` : 'permanent'}
                          </span>
                          {r.storage_folder && (
                            <span className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 truncate max-w-[160px]">
                              dir: {r.storage_folder}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                      {onSelectRecipe && (
                        <button
                          onClick={() => {
                            onSelectRecipe(r);
                            onClose();
                          }}
                          className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-bold transition ${
                            isSelected
                              ? 'bg-purple-600 text-white'
                              : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-purple-50 dark:hover:bg-purple-950/60 hover:text-purple-600'
                          }`}
                        >
                          <Check size={14} weight="bold" />
                          <span>{isSelected ? 'Active' : 'Select'}</span>
                        </button>
                      )}

                      {!r.is_default && (
                        <button
                          onClick={() => handleSetDefault(r.id)}
                          title="Set as Default Recipe"
                          className="p-1.5 rounded-lg text-zinc-400 hover:text-purple-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                        >
                          <Star size={16} />
                        </button>
                      )}

                      <button
                        onClick={() => handleCloneRecipe(r)}
                        title="Clone Recipe"
                        className="p-1.5 rounded-lg text-zinc-400 hover:text-purple-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                      >
                        <Copy size={16} />
                      </button>

                      {!r.is_builtin && (
                        <button
                          onClick={() => handleDeleteRecipe(r.id)}
                          title="Delete Custom Recipe"
                          className="p-1.5 rounded-lg text-zinc-400 hover:text-purple-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition"
                        >
                          <Trash size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
