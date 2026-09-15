import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SystemInfoModal } from './components/SystemInfoModal';
import { JobHistory } from './components/JobHistory';
import { DownloadConfigArea } from './components/DownloadConfigArea';
import { api } from './services/api';
import { SystemInfoResponse, JobResponse, AnalyzeResponse, PresetDefinition } from './types';

vi.mock('./services/api', () => ({
  api: {
    getSettings: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

const mockSystemInfo: SystemInfoResponse = {
  app_name: 'ashoriN',
  app_version: '2.0.0',
  ytdlp_version: '2026.08.30',
  latest_ytdlp_version: '2026.08.30',
  update_available: false,
  ffmpeg_available: true,
  ffmpeg_version: '7.0.2',
  active_jobs: 0,
  max_concurrent_downloads: 2,
  download_retention: 86400,
  temp_retention: 3600,
  max_download_size: '5 GB',
  storage_info: {
    total_bytes: 100 * 1024 * 1024 * 1024,
    used_bytes: 40 * 1024 * 1024 * 1024,
    free_bytes: 60 * 1024 * 1024 * 1024,
    percent_used: 40,
    total_formatted: '100 GB',
    used_formatted: '40 GB',
    free_formatted: '60 GB',
    download_path: '/data/downloads',
    temp_path: '/tmp/ytdlp',
    downloads_bytes: 5 * 1024 * 1024 * 1024,
    downloads_formatted: '5.00 GB',
    retention_enabled: false,
    retention_days: 7,
    next_cleanup_in_seconds: 3600,
  },
};

describe('Storage & Automatic Retention Settings (Requirement 2)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.getSettings).mockResolvedValue({
      retention_enabled: false,
      retention_days: 7,
      allowed_retention_days: [7, 14, 21, 30],
    });
    vi.mocked(api.updateSettings).mockResolvedValue({
      retention_enabled: true,
      retention_days: 14,
      allowed_retention_days: [7, 14, 21, 30],
    });
  });

  it('renders disk usage, downloads size, and retention controls in SystemInfoModal', async () => {
    render(
      <SystemInfoModal
        isOpen={true}
        onClose={vi.fn()}
        systemInfo={mockSystemInfo}
        onUpdateYtDlp={vi.fn()}
        isUpdating={false}
      />
    );

    // Verify storage gauges
    expect(screen.getByText('Storage & Retention')).toBeInTheDocument();
    expect(screen.getByText('5.00 GB')).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();

    // Verify retention toggle (defaults to OFF)
    const toggleBtn = screen.getByRole('switch');
    expect(toggleBtn).toBeInTheDocument();
    expect(toggleBtn).toHaveAttribute('aria-checked', 'false');

    // Toggle retention ON
    fireEvent.click(toggleBtn);
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ retention_enabled: true, retention_days: 7 });
    });
  });

  it('allows changing retention days interval strictly between 7, 14, 21, and 30 days', async () => {
    vi.mocked(api.getSettings).mockResolvedValue({
      retention_enabled: true,
      retention_days: 7,
      allowed_retention_days: [7, 14, 21, 30],
    });

    render(
      <SystemInfoModal
        isOpen={true}
        onClose={vi.fn()}
        systemInfo={mockSystemInfo}
        onUpdateYtDlp={vi.fn()}
        isUpdating={false}
      />
    );

    // Wait for settings to load and select combobox to appear
    const select = await screen.findByRole('combobox', { name: /retention period/i });
    expect(select).toBeInTheDocument();

    // Verify select options: 7, 14, 21, 30
    fireEvent.change(select, { target: { value: '14' } });
    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({ retention_enabled: true, retention_days: 14 });
    });

    // Verify purple confirmation card is shown
    expect(screen.getByText(/Automatic cleanup enabled/i)).toBeInTheDocument();
  });
});

describe('Job History "Automatically removed" Badge', () => {
  const jobs: JobResponse[] = [
    {
      id: 'job-available',
      url: 'https://www.youtube.com/watch?v=111',
      title: 'Active Video on Disk',
      thumbnail: null,
      status: 'COMPLETED',
      progress: 100,
      speed: null,
      eta: null,
      output_filename: 'active.mp4',
      download_url: '/api/download/file/active.mp4',
      error_message: null,
      created_at: 1725184800,
      is_playlist: false,
      is_file_available: true,
    },
    {
      id: 'job-expired',
      url: 'https://www.youtube.com/watch?v=222',
      title: 'Expired Video Removed by Retention Engine',
      thumbnail: null,
      status: 'COMPLETED',
      progress: 100,
      speed: null,
      eta: null,
      output_filename: 'expired.mp4',
      download_url: null,
      error_message: null,
      created_at: 1722506400,
      is_playlist: false,
      is_file_available: false,
    },
  ] as unknown as JobResponse[];

  it('renders download link for available file and purple "Automatically removed" badge for expired file', () => {
    render(
      <JobHistory
        jobs={jobs}
        isOpen={true}
        onClose={vi.fn()}
        onDeleteJob={vi.fn()}
      />
    );

    // Available job has download button
    expect(screen.getByText('Active Video on Disk')).toBeInTheDocument();
    expect(screen.getByText('Save')).toBeInTheDocument();

    // Expired job shows "Automatically removed" badge and NO download file link
    expect(screen.getByText('Expired Video Removed by Retention Engine')).toBeInTheDocument();
    expect(screen.getByText('Automatically removed')).toBeInTheDocument();
  });
});

describe('Mobile Accordions in DownloadConfigArea (Requirement 3)', () => {
  const mockMedia: AnalyzeResponse = {
    url: 'https://www.youtube.com/watch?v=single1',
    title: 'Single Test Video',
    thumbnail: 'https://example.com/thumb.jpg',
    duration: 120,
    duration_string: '02:00',
    uploader: 'Creator',
    webpage_url: 'https://www.youtube.com/watch?v=single1',
    extractor: 'youtube',
    media_type: 'video',
    video_available: true,
    audio_available: true,
    is_playlist: false,
    playlist_id: null,
    entry_count: null,
    video_options: [
      { label: '1080p Full HD', resolution: '1080p', ext: 'mp4', filesize_approx: null, height: 1080 },
    ],
    audio_options: [
      { label: 'MP3 Audio', format: 'mp3', ext: 'mp3' },
    ],
    supported_containers: ['mp4', 'mkv', 'webm', 'mp3'],
    technical_summary: {
      resolution_str: '1080p',
      format_count: 1,
      media_type: 'video',
    },
  };

  const mockPresets: PresetDefinition[] = [
    {
      id: 'recommended',
      name: 'Recommended',
      description: 'Default',
      badge: 'Default',
      config: {
        preset: 'recommended',
        quality: '1080p',
        output_container: 'mp4',
        audio_mode: 'merge',
        audio_format: 'mp3',
        audio_quality: '0',
        video_codec: 'any',
        filename_template: '%(title).150B.%(ext)s',
        subtitles: false,
        embed_subtitles: false,
        auto_subtitles: false,
        subtitle_langs: 'en',
        embed_metadata: true,
        embed_thumbnail: true,
        write_chapters: false,
        retries: 10,
        timeout: 30,
        concurrent_fragments: 1,
        playlist_mode: 'single',
      },
    },
  ];

  it('expands mobile accordion sections on click', () => {
    render(
      <DownloadConfigArea
        media={mockMedia}
        presets={mockPresets}
        onStartDownload={vi.fn()}
        isStarting={false}
      />
    );

    // Switch to Advanced
    const advTab = screen.getByRole('button', { name: /Advanced yt-dlp/i });
    fireEvent.click(advTab);

    // Find and click the 'Video Controls' mobile accordion card button
    const videoAccordionBtns = screen.getAllByRole('button').filter(
      (btn) => btn.textContent?.includes('Video Controls')
    );
    expect(videoAccordionBtns.length).toBeGreaterThan(0);

    // Click to expand Video Controls
    fireEvent.click(videoAccordionBtns[0]);

    // Should show Video Codec Preference
    expect(screen.getByText('Video Codec Preference')).toBeInTheDocument();
  });
});
