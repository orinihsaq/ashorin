import React, { useState, useEffect, useCallback } from 'react';
import {
  Heartbeat,
  ShieldCheck,
  ArrowsClockwise,
  WarningCircle,
  CheckCircle,
  HardDrives,
  Trash,
  FileArrowUp,
  Broom,
  Sparkle,
  TrendUp,
  Check,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import {
  HealthScanModel,
  HealthIssueModel,
  StorageForecastResponse,
} from '../types';

export const MediaHealthView: React.FC = () => {
  const [scan, setScan] = useState<HealthScanModel | null>(null);
  const [issues, setIssues] = useState<HealthIssueModel[]>([]);
  const [forecast, setForecast] = useState<StorageForecastResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isScanning, setIsScanning] = useState(false);
  const [isRepairing, setIsRepairing] = useState(false);
  const [selectedIssueIds, setSelectedIssueIds] = useState<Set<string>>(new Set());
  const [filterType, setFilterType] = useState<string>('all');
  const [repairSuccessBanner, setRepairSuccessBanner] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [latestScan, forecastData] = await Promise.all([
        api.getLatestHealthScan().catch(() => null),
        api.getStorageForecast().catch(() => null),
      ]);
      setScan(latestScan);
      setForecast(forecastData);

      if (latestScan) {
        const issuesData = await api.getHealthIssues(latestScan.id, undefined, true).catch(() => []);
        setIssues(issuesData);
      } else {
        setIssues([]);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRunScan = async () => {
    setIsScanning(true);
    setRepairSuccessBanner(null);
    try {
      const newScan = await api.triggerHealthScan();
      setScan(newScan);
      const [issuesData, forecastData] = await Promise.all([
        api.getHealthIssues(newScan.id, undefined, true).catch(() => []),
        api.getStorageForecast().catch(() => null),
      ]);
      setIssues(issuesData);
      setForecast(forecastData);
      setSelectedIssueIds(new Set());
    } catch (err: any) {
      console.error('Failed to run health scan:', err);
    } finally {
      setIsScanning(false);
    }
  };

  const handleRepairSelected = async () => {
    if (selectedIssueIds.size === 0) return;
    setIsRepairing(true);
    try {
      const res = await api.repairHealthIssues({
        issue_ids: Array.from(selectedIssueIds),
      });
      setRepairSuccessBanner(
        `Repaired ${res.repaired_count} issue(s). Safely freed ${res.freed_formatted || 'storage'}.`
      );
      await loadData();
      setSelectedIssueIds(new Set());
    } catch (err: any) {
      console.error('Repair failed:', err);
    } finally {
      setIsRepairing(false);
    }
  };

  const handleQuickRepair = async (repairType: 'clean_incomplete' | 'reindex_orphans' | 'remove_stale') => {
    setIsRepairing(true);
    try {
      const res = await api.repairHealthIssues({ repair_type: repairType });
      setRepairSuccessBanner(
        `Action complete: repaired ${res.repaired_count} issue(s) (${res.freed_formatted || '0 B'} freed).`
      );
      await loadData();
      setSelectedIssueIds(new Set());
    } catch (err: any) {
      console.error('Quick repair failed:', err);
    } finally {
      setIsRepairing(false);
    }
  };

  const handleToggleSelectIssue = (id: string) => {
    setSelectedIssueIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSelectAllFiltered = () => {
    if (filteredIssues.length === 0) return;
    const allSelected = filteredIssues.every((i) => selectedIssueIds.has(i.id));
    if (allSelected) {
      setSelectedIssueIds(new Set());
    } else {
      setSelectedIssueIds(new Set(filteredIssues.map((i) => i.id)));
    }
  };

  const filteredIssues = issues.filter((i) => {
    if (filterType === 'all') return true;
    return i.issue_type === filterType;
  });

  const issueCounts = {
    all: issues.length,
    incomplete_download: issues.filter((i) => i.issue_type === 'incomplete_download').length,
    orphaned_record: issues.filter((i) => i.issue_type === 'orphaned_record').length,
    missing_file: issues.filter((i) => i.issue_type === 'missing_file').length,
    duplicate_media: issues.filter((i) => i.issue_type === 'duplicate_media').length,
  };

  return (
    <div className="max-w-6xl w-full mx-auto px-3 sm:px-6 py-6 sm:py-8 space-y-6 animate-fade-in min-w-0">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-purple-100 dark:bg-purple-950/80 text-purple-600 dark:text-purple-400">
              <Heartbeat size={20} weight="fill" />
            </span>
            <h1 className="text-xl sm:text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
              Media Health <span className="text-purple-600 dark:text-purple-400">Center</span>
            </h1>
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded-md bg-purple-50 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/60">
              Diagnostic Audit
            </span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 max-w-xl">
            Non-destructive library audit, storage forecasting, partial cleanup, and automated orphan recovery.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={handleRunScan}
            disabled={isScanning}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 transition shadow-sm"
          >
            <ArrowsClockwise size={15} className={isScanning ? 'animate-spin' : ''} />
            <span>{isScanning ? 'Scanning Storage...' : 'Scan Library Now'}</span>
          </button>
        </div>
      </div>

      {/* Safety Guarantee Alert */}
      <div className="p-4 rounded-2xl bg-purple-50/70 dark:bg-purple-950/30 border border-purple-200/80 dark:border-purple-800/60 flex items-start gap-3 shadow-xs">
        <ShieldCheck size={20} weight="fill" className="text-purple-600 dark:text-purple-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-0.5">
          <p className="font-bold text-purple-900 dark:text-purple-200">
            Non-Destructive Guarantee
          </p>
          <p className="text-purple-800/80 dark:text-purple-300/80">
            Protected media, favorited downloads, and actively running extraction jobs are strictly safeguarded and will never be removed by audit repairs.
          </p>
        </div>
      </div>

      {/* Success Banner */}
      {repairSuccessBanner && (
        <div className="p-3 bg-purple-100 dark:bg-purple-950/60 border border-purple-300 dark:border-purple-800 rounded-xl flex items-center justify-between text-xs text-purple-900 dark:text-purple-100 animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle size={18} weight="fill" className="text-purple-600 dark:text-purple-400" />
            <span>{repairSuccessBanner}</span>
          </div>
          <button
            onClick={() => setRepairSuccessBanner(null)}
            className="text-purple-600 hover:text-purple-800 dark:text-purple-400 text-xs font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Initial loading state */}
      {isLoading && !scan && (
        <div className="py-12 text-center text-xs text-zinc-500">
          <div className="w-6 h-6 rounded-full border-2 border-purple-600 border-t-transparent animate-spin mx-auto mb-2" />
          <span>Auditing media health status...</span>
        </div>
      )}

      {/* Primary KPI Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-[11px] font-bold uppercase tracking-wider">
            <span>Files Scanned</span>
            <HardDrives size={16} className="text-purple-500" />
          </div>
          <p className="text-2xl font-black font-mono text-zinc-900 dark:text-zinc-100">
            {scan ? scan.files_scanned.toLocaleString() : '—'}
          </p>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
            {scan?.completed_at ? `Audited ${new Date(scan.completed_at).toLocaleTimeString()}` : 'No scan on record'}
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-[11px] font-bold uppercase tracking-wider">
            <span>Healthy Media</span>
            <CheckCircle size={16} className="text-purple-500" />
          </div>
          <p className="text-2xl font-black font-mono text-purple-600 dark:text-purple-400">
            {scan ? Math.max(0, scan.files_scanned - scan.issues_found).toLocaleString() : '—'}
          </p>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
            Verified with zero corruptions
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-[11px] font-bold uppercase tracking-wider">
            <span>Issues Detected</span>
            <WarningCircle size={16} className="text-purple-500" />
          </div>
          <p className="text-2xl font-black font-mono text-zinc-900 dark:text-zinc-100">
            {scan ? scan.issues_found.toLocaleString() : '—'}
          </p>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
            {issues.length} currently unresolved
          </p>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 dark:text-zinc-400 text-[11px] font-bold uppercase tracking-wider">
            <span>Recoverable Space</span>
            <Broom size={16} className="text-purple-500" />
          </div>
          <p className="text-2xl font-black font-mono text-purple-600 dark:text-purple-400">
            {scan ? scan.storage_recoverable_formatted : '0 B'}
          </p>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400">
            From partial & orphaned artifacts
          </p>
        </div>
      </div>

      {/* Storage Growth & Forecasting Section */}
      {forecast && (
        <div className="p-5 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <TrendUp size={18} className="text-purple-500" />
              <h2 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
                Storage Capacity & Ingestion Forecast
              </h2>
            </div>
            <div className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400">
              {(forecast.free_bytes / (1024 * 1024 * 1024)).toFixed(1)} GB Free of {(forecast.total_bytes / (1024 * 1024 * 1024)).toFixed(1)} GB Total
            </div>
          </div>

          {/* Storage Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono text-zinc-600 dark:text-zinc-300">
              <span>{forecast.percent_used.toFixed(1)}% Used</span>
              <span>{(100 - forecast.percent_used).toFixed(1)}% Available</span>
            </div>
            <div className="w-full h-3 rounded-full bg-zinc-100 dark:bg-zinc-800 overflow-hidden p-0.5">
              <div
                className="h-full rounded-full bg-gradient-to-r from-purple-800 via-purple-600 to-purple-400 transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(2, forecast.percent_used))}%` }}
              />
            </div>
          </div>

          {/* Forecasting Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs">
            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Daily Growth Rate</span>
              <span className="text-sm font-black font-mono text-zinc-900 dark:text-zinc-100 mt-0.5 block">
                {forecast.daily_download_rate_formatted}
              </span>
              <span className="text-[10px] text-zinc-500">Based on recent ingestion history</span>
            </div>

            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Low Storage Runway</span>
              <span className="text-sm font-black font-mono text-purple-600 dark:text-purple-400 mt-0.5 block">
                {forecast.days_until_low_space ? `~${forecast.days_until_low_space} days remaining` : 'Ample headroom'}
              </span>
              <span className="text-[10px] text-zinc-500">Threshold: &lt;10% free capacity</span>
            </div>

            <div className="p-3 rounded-xl bg-zinc-50 dark:bg-zinc-950/60 border border-zinc-200/80 dark:border-zinc-800">
              <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Recommendation</span>
              <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 mt-0.5 block line-clamp-2">
                {forecast.status_summary}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Quick Action Presets */}
      <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-1.5">
            <Sparkle size={15} className="text-purple-500" />
            <span>Automated Safe Maintenance</span>
          </h3>
          <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">
            One-click safe maintenance operations.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => handleQuickRepair('clean_incomplete')}
            disabled={isRepairing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 transition"
          >
            <Broom size={14} className="text-purple-500" />
            <span>Clean Incomplete Parts</span>
          </button>

          <button
            onClick={() => handleQuickRepair('reindex_orphans')}
            disabled={isRepairing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 transition"
          >
            <FileArrowUp size={14} className="text-purple-500" />
            <span>Reindex Orphan Files</span>
          </button>

          <button
            onClick={() => handleQuickRepair('remove_stale')}
            disabled={isRepairing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 transition"
          >
            <Trash size={14} className="text-purple-500" />
            <span>Purge Stale Missing Rows</span>
          </button>
        </div>
      </div>

      {/* Issues Management List */}
      <div className="rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-sm overflow-hidden space-y-3 p-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-100 dark:border-zinc-800 pb-4">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
              Detected Issues
            </h3>
            <span className="px-2 py-0.5 text-[11px] font-mono font-bold rounded-full bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
              {filteredIssues.length}
            </span>
          </div>

          {/* Issue Type Filters */}
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'all', label: `All (${issueCounts.all})` },
              { id: 'incomplete_download', label: `Partials (${issueCounts.incomplete_download})` },
              { id: 'orphaned_record', label: `Orphans (${issueCounts.orphaned_record})` },
              { id: 'missing_file', label: `Missing (${issueCounts.missing_file})` },
              { id: 'duplicate_media', label: `Duplicates (${issueCounts.duplicate_media})` },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setFilterType(f.id)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition ${
                  filterType === f.id
                    ? 'bg-purple-600 text-white shadow-xs'
                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-200'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Action toolbar for issue selection */}
        {filteredIssues.length > 0 && (
          <div className="flex items-center justify-between gap-2 pt-1">
            <button
              onClick={handleSelectAllFiltered}
              className="text-xs font-semibold text-purple-600 dark:text-purple-400 hover:underline"
            >
              {filteredIssues.every((i) => selectedIssueIds.has(i.id))
                ? 'Deselect All'
                : 'Select All Filtered'}
            </button>

            {selectedIssueIds.size > 0 && (
              <button
                onClick={handleRepairSelected}
                disabled={isRepairing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-white bg-purple-600 hover:bg-purple-700 disabled:opacity-50 transition shadow-sm"
              >
                <Broom size={14} />
                <span>Safely Repair ({selectedIssueIds.size}) Selected</span>
              </button>
            )}
          </div>
        )}

        {/* Issue Items */}
        {filteredIssues.length === 0 ? (
          <div className="py-12 text-center text-xs text-zinc-500 dark:text-zinc-400 space-y-2">
            <CheckCircle size={32} weight="fill" className="text-purple-500 mx-auto" />
            <p className="font-bold text-zinc-800 dark:text-zinc-200">
              {filterType === 'all'
                ? 'Library and storage are completely healthy'
                : 'No issues found in this category'}
            </p>
            <p className="text-[11px] text-zinc-400">
              All files match database catalogs with no orphaned temp artifacts.
            </p>
          </div>
        ) : (
          <div className="space-y-2 pt-1">
            {filteredIssues.map((issue) => {
              const isSelected = selectedIssueIds.has(issue.id);
              return (
                <div
                  key={issue.id}
                  onClick={() => handleToggleSelectIssue(issue.id)}
                  className={`p-3 rounded-xl border transition cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isSelected
                      ? 'border-purple-600 bg-purple-50/40 dark:bg-purple-950/20'
                      : 'border-zinc-200 dark:border-zinc-800 hover:border-purple-300 dark:hover:border-purple-800/60'
                  }`}
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <div
                      className={`w-4 h-4 rounded mt-0.5 shrink-0 border flex items-center justify-center transition ${
                        isSelected
                          ? 'bg-purple-600 border-purple-600 text-white'
                          : 'border-zinc-300 dark:border-zinc-700'
                      }`}
                    >
                      {isSelected && <Check size={12} weight="bold" />}
                    </div>

                    <div className="space-y-0.5 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded bg-purple-100 dark:bg-purple-950 text-purple-700 dark:text-purple-300">
                          {issue.issue_type.replace('_', ' ')}
                        </span>
                        <span className="text-[11px] font-semibold text-zinc-800 dark:text-zinc-200 truncate">
                          {issue.details?.title || issue.file_path || 'Storage anomaly'}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 font-mono truncate">
                        {issue.file_path || issue.details?.suggested_action || 'No path available'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                    {issue.details?.size_formatted && (
                      <span className="text-[11px] font-mono font-semibold text-zinc-600 dark:text-zinc-400">
                        {issue.details.size_formatted}
                      </span>
                    )}
                    <span className="text-[10px] font-bold text-purple-600 dark:text-purple-400 uppercase tracking-wider">
                      {issue.details?.suggested_action || 'Safe Repair'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
