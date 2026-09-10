import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { UrlInput } from './components/UrlInput';
import { MediaWorkspace } from './components/MediaWorkspace';
import { DownloadConfigArea } from './components/DownloadConfigArea';
import { DownloadProgress } from './components/DownloadProgress';
import { JobHistory } from './components/JobHistory';
import { SystemInfoModal } from './components/SystemInfoModal';
import { ErrorAlert } from './components/ErrorAlert';
import { Footer } from './components/Footer';
import { useTheme } from './hooks/useTheme';
import { useJobEvents } from './hooks/useJobEvents';
import { api } from './services/api';
import {
  AnalyzeResponse,
  DownloadConfig,
  JobResponse,
  PresetDefinition,
  SystemInfoResponse,
} from './types';

export const App: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isStartingDownload, setIsStartingDownload] = useState(false);
  const [media, setMedia] = useState<AnalyzeResponse | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [presets, setPresets] = useState<PresetDefinition[]>([]);
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSystemInfoOpen, setIsSystemInfoOpen] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [isUpdatingYtDlp, setIsUpdatingYtDlp] = useState(false);

  // Subscribe to real-time events for the active download job
  const { job: activeJob } = useJobEvents(currentJobId);

  // Load presets, system info, and recent jobs on mount
  const refreshPresets = useCallback(async () => {
    try {
      const data = await api.getPresets();
      setPresets(data.presets);
    } catch (err) {
      console.error('Failed to load presets:', err);
    }
  }, []);

  const refreshSystemInfo = useCallback(async () => {
    try {
      const data = await api.getSystemInfo();
      setSystemInfo(data);
    } catch (err) {
      console.error('Failed to load system info:', err);
    }
  }, []);

  const refreshJobs = useCallback(async () => {
    try {
      const data = await api.getJobs();
      setJobs(data.jobs);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    }
  }, []);

  useEffect(() => {
    refreshPresets();
    refreshSystemInfo();
    refreshJobs();
  }, [refreshPresets, refreshSystemInfo, refreshJobs]);

  // When active job updates from SSE, sync with jobs list
  useEffect(() => {
    if (activeJob) {
      setJobs((prev) => {
        const idx = prev.findIndex((j) => j.id === activeJob.id);
        if (idx >= 0) {
          const updated = [...prev];
          updated[idx] = activeJob;
          return updated;
        }
        return [activeJob, ...prev];
      });
    }
  }, [activeJob]);

  // Handle URL Analysis
  const handleAnalyze = async (targetUrl: string) => {
    setErrorMessage(null);
    setMedia(null);
    setCurrentJobId(null);
    setIsAnalyzing(true);

    try {
      const result = await api.analyzeUrl(targetUrl);
      setMedia(result);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to inspect media. Please verify the URL.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Download Submission with structured DownloadConfig
  const handleStartDownload = async (config: DownloadConfig) => {
    if (!media) return;
    setErrorMessage(null);
    setIsStartingDownload(true);

    try {
      const res = await api.startDownload({
        url: media.url,
        title: media.title,
        config: config,
      });

      setCurrentJobId(res.job_id);
      refreshJobs();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to queue download job.');
    } finally {
      setIsStartingDownload(false);
    }
  };

  // Handle Job Cancellation
  const handleCancel = async (jobId: string) => {
    try {
      await api.cancelJob(jobId);
      refreshJobs();
    } catch (err: any) {
      console.error('Error cancelling job:', err);
    }
  };

  // Handle Job Deletion
  const handleDeleteJob = async (jobId: string) => {
    try {
      await api.deleteJob(jobId);
      if (currentJobId === jobId) {
        setCurrentJobId(null);
      }
      refreshJobs();
    } catch (err: any) {
      console.error('Error deleting job:', err);
    }
  };

  // Reset workflow for new media
  const handleReset = () => {
    setMedia(null);
    setCurrentJobId(null);
    setUrl('');
    setErrorMessage(null);
  };

  // Handle manual yt-dlp update
  const handleUpdateYtDlp = async () => {
    setIsUpdatingYtDlp(true);
    try {
      await api.updateYtDlp();
      await refreshSystemInfo();
    } finally {
      setIsUpdatingYtDlp(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-between selection:bg-brand-500 selection:text-white">
      {/* Header */}
      <Header
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenSystemInfo={() => setIsSystemInfoOpen(true)}
        onToggleHistory={() => setIsHistoryOpen((prev) => !prev)}
        historyCount={jobs.length}
        systemInfo={systemInfo}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        {/* Hero Section */}
        <div className="text-center space-y-2.5">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-brand-50 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800/60 shadow-xs">
            <span>PRECISION MEDIA EXTRACTION</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-black tracking-tight text-zinc-900 dark:text-zinc-50 font-sans">
            ashori<span className="text-brand-600 dark:text-brand-400">N</span>
          </h2>

          <p className="text-xs sm:text-sm text-zinc-600 dark:text-zinc-400 max-w-lg mx-auto leading-relaxed">
            High-performance self-hosted media extraction engine. Selectable optimization presets, granular yt-dlp parameter controls, and native FFmpeg stream muxing.
          </p>
        </div>

        {/* URL Input Form */}
        <UrlInput
          url={url}
          setUrl={setUrl}
          onAnalyze={handleAnalyze}
          isLoading={isAnalyzing}
        />

        {/* Error Alert Display */}
        <ErrorAlert
          message={errorMessage}
          onDismiss={() => setErrorMessage(null)}
        />

        {/* Real-time Download Progress Card (if a job is active or completed) */}
        {activeJob && (
          <DownloadProgress
            job={activeJob}
            onCancel={handleCancel}
            onReset={handleReset}
          />
        )}

        {/* Media Details & Format Selection (if analyzed and no job currently running) */}
        {media && !activeJob && (
          <div className="space-y-5 animate-in fade-in duration-300">
            <MediaWorkspace media={media} />
            <DownloadConfigArea
              media={media}
              presets={presets}
              onStartDownload={handleStartDownload}
              isStarting={isStartingDownload}
            />
          </div>
        )}
      </main>

      {/* History Drawer */}
      <JobHistory
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        jobs={jobs}
        onDeleteJob={handleDeleteJob}
      />

      {/* System Diagnostics Modal */}
      <SystemInfoModal
        isOpen={isSystemInfoOpen}
        onClose={() => setIsSystemInfoOpen(false)}
        systemInfo={systemInfo}
        onUpdateYtDlp={handleUpdateYtDlp}
        isUpdating={isUpdatingYtDlp}
      />

      {/* Footer */}
      <Footer />
    </div>
  );
};

export default App;
