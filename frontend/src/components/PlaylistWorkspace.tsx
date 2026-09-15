import React, { useState, useMemo } from 'react';
import {
  AnalyzeResponse,
  DownloadConfig,
  PresetDefinition,
  RecipeModel,
} from '../types';
import { PlaylistHero } from './PlaylistHero';
import { PlaylistSelectionToolbar } from './PlaylistSelectionToolbar';
import { PlaylistItemList } from './PlaylistItemList';
import { DownloadConfigArea } from './DownloadConfigArea';

interface PlaylistWorkspaceProps {
  media: AnalyzeResponse;
  presets: PresetDefinition[];
  onStartDownload: (config: DownloadConfig) => void;
  isStarting: boolean;
  onKeepSynced?: () => void;
  onPreflight?: (config: DownloadConfig) => void;
  onOpenRecipes?: () => void;
  selectedRecipe?: RecipeModel | null;
}

export const PlaylistWorkspace: React.FC<PlaylistWorkspaceProps> = ({
  media,
  presets,
  onStartDownload,
  isStarting,
  onKeepSynced,
  onPreflight,
  onOpenRecipes,
  selectedRecipe,
}) => {
  const entries = useMemo(() => media.entries || [], [media.entries]);
  const totalCount = entries.length;

  const [playlistMode, setPlaylistMode] = useState<'all' | 'selected' | 'single'>('all');

  // Initialize with all items selected
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    () => new Set(entries.map((e) => e.index))
  );

  const handleSelectAll = () => {
    setSelectedIndices(new Set(entries.map((e) => e.index)));
  };

  const handleDeselectAll = () => {
    setSelectedIndices(new Set());
  };

  const handleInvert = () => {
    setSelectedIndices((prev) => {
      const next = new Set<number>();
      for (const e of entries) {
        if (!prev.has(e.index)) {
          next.add(e.index);
        }
      }
      return next;
    });
  };

  const handleApplyRange = (start: number, end: number) => {
    const next = new Set<number>();
    for (let i = start; i <= end; i++) {
      next.add(i);
    }
    setSelectedIndices(next);
    setPlaylistMode('selected');
  };

  const handleToggleIndex = (index: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
    if (playlistMode === 'all') {
      setPlaylistMode('selected');
    }
  };

  const handleDownloadSubmit = (baseConfig: DownloadConfig) => {
    const enrichedConfig: DownloadConfig = {
      ...baseConfig,
      playlist_mode: playlistMode === 'single' ? 'single' : playlistMode === 'all' ? 'all' : 'selected',
    };

    if (playlistMode === 'selected') {
      enrichedConfig.selected_indices = Array.from(selectedIndices).sort((a, b) => a - b);
    }

    onStartDownload(enrichedConfig);
  };

  const handlePreflightSubmit = (baseConfig: DownloadConfig) => {
    if (!onPreflight) return;
    const enrichedConfig: DownloadConfig = {
      ...baseConfig,
      playlist_mode: playlistMode === 'single' ? 'single' : playlistMode === 'all' ? 'all' : 'selected',
    };
    if (playlistMode === 'selected') {
      enrichedConfig.selected_indices = Array.from(selectedIndices).sort((a, b) => a - b);
    }
    onPreflight(enrichedConfig);
  };

  return (
    <div className="space-y-5 animate-in fade-in duration-300">
      {/* Hero Overview */}
      <PlaylistHero
        media={media}
        playlistMode={playlistMode}
        onChangeMode={setPlaylistMode}
        selectedCount={selectedIndices.size}
        onKeepSynced={onKeepSynced}
      />

      {/* Item List and Selection Controls (visible when in playlist mode) */}
      {playlistMode !== 'single' && (
        <div className="space-y-3">
          <PlaylistSelectionToolbar
            totalCount={totalCount}
            selectedCount={selectedIndices.size}
            onSelectAll={handleSelectAll}
            onDeselectAll={handleDeselectAll}
            onInvert={handleInvert}
            onApplyRange={handleApplyRange}
          />

          <PlaylistItemList
            entries={entries}
            selectedIndices={selectedIndices}
            onToggleIndex={handleToggleIndex}
          />
        </div>
      )}

      {/* Download Configuration & Action Area */}
      <DownloadConfigArea
        media={media}
        presets={presets}
        onStartDownload={handleDownloadSubmit}
        isStarting={isStarting}
        onPreflight={onPreflight ? handlePreflightSubmit : undefined}
        onOpenRecipes={onOpenRecipes}
        selectedRecipe={selectedRecipe}
      />
    </div>
  );
};
