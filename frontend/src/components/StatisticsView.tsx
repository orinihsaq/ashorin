import React, { useEffect, useState } from 'react';
import {
  ChartBar,
  DownloadSimple,
  HardDrives,
  TrendUp,
} from '@phosphor-icons/react';
import { api } from '../services/api';
import { StatisticsResponse } from '../types';

export const StatisticsView: React.FC = () => {
  const [stats, setStats] = useState<StatisticsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getStatistics();
        setStats(data);
      } catch (err) {
        console.error('Failed to load statistics', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  if (loading) {
    return <div className="py-20 text-center text-xs text-zinc-500">Loading analytics...</div>;
  }

  if (!stats) {
    return <div className="py-20 text-center text-xs text-zinc-500">No telemetry available.</div>;
  }

  const successRate =
    stats.total_downloads > 0
      ? Math.round((stats.completed_downloads / stats.total_downloads) * 100)
      : 100;

  const maxDailyCount = Math.max(...stats.downloads_by_day.map((d) => d.count), 1);

  return (
    <div className="w-full max-w-5xl mx-auto px-3 sm:px-6 py-6 space-y-6 min-w-0">
      {/* Header */}
      <div className="pb-4 border-b border-zinc-200 dark:border-zinc-800">
        <h1 className="text-xl sm:text-2xl font-black text-zinc-900 dark:text-zinc-100 tracking-tight">
          System <span className="text-purple-600 dark:text-purple-400">Analytics</span>
        </h1>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
          Download pipeline telemetry, storage consumption, and format distribution
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span>Total Downloads</span>
            <DownloadSimple size={16} className="text-purple-600 dark:text-purple-400" />
          </div>
          <p className="text-2xl font-black font-mono text-zinc-900 dark:text-zinc-100">
            {stats.total_downloads}
          </p>
          <p className="text-[11px] text-zinc-400 font-mono">
            {stats.completed_downloads} completed • {stats.failed_downloads} failed
          </p>
        </div>

        <div className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span>Data Downloaded</span>
            <HardDrives size={16} className="text-purple-600 dark:text-purple-400" />
          </div>
          <p className="text-2xl font-black font-mono text-purple-600 dark:text-purple-400">
            {stats.total_formatted}
          </p>
          <p className="text-[11px] text-zinc-400 font-mono">Bandwidth transferred</p>
        </div>

        <div className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span>Success Rate</span>
            <TrendUp size={16} className="text-purple-600 dark:text-purple-400" />
          </div>
          <p className="text-2xl font-black font-mono text-zinc-900 dark:text-zinc-100">
            {successRate}%
          </p>
          <p className="text-[11px] text-zinc-400 font-mono">Resilient extraction</p>
        </div>

        <div className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-1">
          <div className="flex items-center justify-between text-zinc-500 text-xs">
            <span>Current Pipeline</span>
            <ChartBar size={16} className="text-purple-600 dark:text-purple-400" />
          </div>
          <p className="text-2xl font-black font-mono text-zinc-900 dark:text-zinc-100">
            {stats.active_downloads + stats.queued_downloads}
          </p>
          <p className="text-[11px] text-zinc-400 font-mono">
            {stats.active_downloads} running • {stats.queued_downloads} queued
          </p>
        </div>
      </div>

      {/* 7-Day Activity Chart */}
      <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
          7-Day Download Activity
        </h3>
        <div className="h-40 flex items-end justify-between gap-2 pt-4 px-2">
          {stats.downloads_by_day.map((d, i) => {
            const heightPct = Math.max(12, Math.round((d.count / maxDailyCount) * 100));
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-2 group">
                <span className="text-[10px] font-mono text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity">
                  {d.count}
                </span>
                <div className="w-full bg-zinc-100 dark:bg-zinc-800 rounded-lg h-28 flex items-end p-1">
                  <div
                    className="w-full bg-gradient-to-t from-purple-800 to-purple-500 rounded-md transition-all duration-500"
                    style={{ height: `${heightPct}%` }}
                  />
                </div>
                <span className="text-[10px] font-medium text-zinc-500 truncate max-w-full text-center block" title={d.date}>{d.date}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top Extractors & Containers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Top Extractors */}
        <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
            Top Media Sources
          </h3>
          {stats.top_extractors.length === 0 ? (
            <p className="text-xs text-zinc-400 py-4 text-center">No source telemetry yet</p>
          ) : (
            <div className="space-y-2">
              {stats.top_extractors.map((ext, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-xl bg-zinc-50 dark:bg-zinc-950 text-xs"
                >
                  <span className="font-semibold text-zinc-700 dark:text-zinc-300">
                    {ext.name}
                  </span>
                  <span className="font-mono font-bold text-purple-600 dark:text-purple-400">
                    {ext.count} files
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Formats */}
        <div className="p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-3">
          <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">
            Format Breakdown
          </h3>
          {stats.top_containers.length === 0 ? (
            <p className="text-xs text-zinc-400 py-4 text-center">No format telemetry yet</p>
          ) : (
            <div className="space-y-2">
              {stats.top_containers.map((cont, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-xl bg-zinc-50 dark:bg-zinc-950 text-xs"
                >
                  <span className="font-mono font-bold text-zinc-700 dark:text-zinc-300">
                    {cont.format}
                  </span>
                  <span className="font-mono text-zinc-500">
                    {cont.count} downloads
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
