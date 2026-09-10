import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { UrlInput } from './components/UrlInput';
import { MediaCard } from './components/MediaCard';
import { FormatSelector } from './components/FormatSelector';
import { DownloadProgress } from './components/DownloadProgress';
import { JobHistory } from './components/JobHistory';
import { SystemInfoModal } from './components/SystemInfoModal';
import { ErrorAlert } from './components/ErrorAlert';
import { Footer } from './components/Footer';
import { useTheme } from './hooks/useTheme';
import { useJobEvents } from './hooks/useJobEvents';
import { api } from './services/api';
import { AnalyzeResponse, JobResponse, SystemInfoResponse } from './types';

export const App: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  const [url, setUrl] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isStartingDownload, setIsStartingDownload] = useState(false);
  const [media, setMedia] = useState<AnalyzeResponse | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [isSystemInfoOpen, setIsSystemInfoOpen] = useState(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [isUpdatingYtDlp, setIsUpdatingYtDlp] = useState(false);

  // Subscribe to real-time events for the active download job
  const { job: activeJob } = useJobEvents(currentJobId);

  // Load system info and recent jobs on mount
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
    refreshSystemInfo();
    refreshJobs();
  }, [refreshSystemInfo, refreshJobs]);

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
      setErrorMessage(err.message || 'Failed to analyze URL. Please verify the link.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle Download Submission
  const handleStartDownload = async (params: {
    resolution: string;
    audio_only: boolean;
    audio_format: string;
    output_container: string;
  }) => {
    if (!media) return;
    setErrorMessage(null);
    setIsStartingDownload(true);

    try {
      const res = await api.startDownload({
        url: media.url,
        title: media.title,
        resolution: params.resolution,
        audio_only: params.audio_only,
        audio_format: params.audio_format,
        output_container: params.output_container,
      });

      setCurrentJobId(res.job_id);
      refreshJobs();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to queue download.');
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

  // Reset workflow
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
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-8 sm:py-12 space-y-8">
        {/* Hero Section Header */}
        <div className="text-center space-y-2">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Media Downloader
          </h2>
          <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-md mx-auto">
            Download media from supported websites with selectable resolutions, audio extraction, and real-time progress.
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
            <MediaCard media={media} />
            <FormatSelector
              media={media}
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

      {/* System Info Modal */}
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
