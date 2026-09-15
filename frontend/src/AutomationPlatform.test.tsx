import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';

vi.mock('./services/api', () => ({
  api: {
    getPresets: vi.fn().mockResolvedValue({
      presets: [
        {
          id: 'recommended',
          name: 'Recommended',
          description: 'Balanced MP4 with metadata',
          badge: 'Default',
          config: {
            preset: 'recommended',
            quality: 'best',
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
      ],
      default_preset: 'recommended',
    }),
    getSystemInfo: vi.fn().mockResolvedValue({
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
      max_download_size: '10G',
      storage_info: {
        total_bytes: 250000000000,
        used_bytes: 120000000000,
        free_bytes: 130000000000,
        percent_used: 48.0,
        free_formatted: '121.0 GB',
        total_formatted: '232.8 GB',
        used_formatted: '111.8 GB',
      },
    }),
    getJobs: vi.fn().mockResolvedValue({
      jobs: [],
      total: 0,
      active_count: 0,
    }),
    getProfiles: vi.fn().mockResolvedValue([
      {
        id: 'recommended',
        name: 'Recommended',
        description: 'Balanced MP4 with metadata',
        badge: 'Default',
        is_default: true,
        is_builtin: true,
        config: {},
      },
    ]),
    evaluateRules: vi.fn().mockResolvedValue({
      matched: true,
      rule_name: 'Default Fallback',
      profile_id: 'recommended',
      profile_name: 'Recommended',
      reason: 'Applied profile: Recommended',
    }),
    getLibrary: vi.fn().mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    }),
    getStorageSummary: vi.fn().mockResolvedValue({
      total_bytes: 1048576,
      total_formatted: '1.0 MB',
      total_items: 1,
      video_count: 1,
      audio_count: 0,
      playlist_count: 0,
      video_bytes: 1048576,
      audio_bytes: 0,
      playlist_bytes: 0,
      favorites_count: 0,
      protected_count: 0,
      recent_items: [],
    }),
    getStatistics: vi.fn().mockResolvedValue({
      total_downloads: 12,
      completed_downloads: 11,
      failed_downloads: 1,
      cancelled_downloads: 0,
      total_bytes_downloaded: 524288000,
      total_formatted: '500.0 MB',
      active_downloads: 0,
      queued_downloads: 0,
      top_extractors: [{ name: 'youtube', count: 10 }],
      top_containers: [{ format: 'mp4', count: 11 }],
      downloads_by_day: [{ date: '2026-09-10', count: 12 }],
    }),
    getQueue: vi.fn().mockResolvedValue({
      queued: [],
      active: [],
      completed: [],
      failed: [],
      stats: { total: 0, queued: 0, active: 0, completed: 0, failed: 0 },
    }),
    getRules: vi.fn().mockResolvedValue([]),
    getKeys: vi.fn().mockResolvedValue([]),
    getWebhooks: vi.fn().mockResolvedValue([]),
    getSettings: vi.fn().mockResolvedValue({
      auto_retention_days: 0,
      retention_enabled: false,
    }),
    getRecipes: vi.fn().mockResolvedValue([
      {
        id: 'video_archive',
        name: 'Video Archive',
        description: 'Best video and audio merged',
        profile_id: 'recommended',
        storage_folder: 'Videos/{title}',
        duplicate_policy: 'skip',
        target_quality: 'best',
        minimum_quality: '720p',
        upgrade_policy: 'upgrade_if_better',
        retention_days: 0,
        notify_events: ['download_completed'],
        is_builtin: true,
        is_default: true,
        created_at: 1700000000,
        updated_at: 1700000000,
      },
    ]),
    getWatchers: vi.fn().mockResolvedValue([]),
    getLatestHealthScan: vi.fn().mockResolvedValue({
      id: 'scan-1',
      started_at: 1700000000,
      completed_at: 1700000010,
      status: 'completed',
      files_scanned: 42,
      issues_found: 0,
      issues_repaired: 0,
      storage_recoverable_bytes: 0,
      storage_recoverable_formatted: '0 B',
      summary: {},
      issues: [],
    }),
    getHealthIssues: vi.fn().mockResolvedValue([]),
    getStorageForecast: vi.fn().mockResolvedValue({
      total_bytes: 200000000000,
      used_bytes: 50000000000,
      free_bytes: 150000000000,
      percent_used: 25.0,
      daily_download_rate_bytes: 100000000,
      daily_download_rate_formatted: '100.0 MB / day',
      days_until_low_space: 450,
      potential_recoverable_bytes: 0,
      potential_recoverable_formatted: '0 B',
      status_summary: 'Storage headroom is healthy.',
    }),
    runPreflight: vi.fn().mockResolvedValue({
      title: 'Test Video',
      is_playlist: false,
      total_items: 1,
      selected_items: 1,
      new_items_count: 1,
      existing_items_count: 0,
      upgrade_items_count: 0,
      unavailable_items_count: 0,
      estimated_total_bytes: 15000000,
      estimated_total_formatted: '15.0 MB',
      disk_free_bytes: 100000000000,
      disk_free_formatted: '100.0 GB',
      storage_status: 'sufficient',
      storage_message: 'Adequate disk space',
      resolved_profile_id: 'recommended',
      resolved_profile_name: 'Recommended',
      destination_folder: '/downloads',
      items: [],
      explanations: [],
    }),
    analyzeUrl: vi.fn(),
    startDownload: vi.fn(),
    cancelJob: vi.fn(),
    deleteJob: vi.fn(),
    updateYtDlp: vi.fn(),
  },
}));

describe('ashoriN Media Automation Platform Features', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all header navigation tabs', () => {
    render(<App />);
    expect(screen.getAllByRole('button', { name: /Downloader/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('button', { name: /Queue/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('button', { name: /Library/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('button', { name: /Analytics/i }).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByRole('button', { name: /Settings/i }).length).toBeGreaterThanOrEqual(1);
  });

  it('navigates between views when tabs are clicked', async () => {
    render(<App />);

    // Click Queue tab
    fireEvent.click(screen.getAllByRole('button', { name: /Queue/i })[0]);
    expect(await screen.findByText(/Active download pipeline/i)).toBeInTheDocument();

    // Click Library tab
    fireEvent.click(screen.getAllByRole('button', { name: /Library/i })[0]);
    expect(await screen.findByPlaceholderText(/Search library/i)).toBeInTheDocument();

    // Click Analytics tab
    fireEvent.click(screen.getAllByRole('button', { name: /Analytics/i })[0]);
    expect(await screen.findByText(/Download pipeline telemetry/i)).toBeInTheDocument();

    // Click Settings tab
    fireEvent.click(screen.getAllByRole('button', { name: /Settings/i })[0]);
    expect(await screen.findByText(/Automatic Deletion/i)).toBeInTheDocument();

    // Return to Downloader tab
    fireEvent.click(screen.getAllByRole('button', { name: /Downloader/i })[0]);
    expect(await screen.findByPlaceholderText(/Paste media link/i)).toBeInTheDocument();
  });

  it('opens and closes the Batch Import modal', async () => {
    render(<App />);

    // Find and click the Batch button next to URL input
    const batchBtn = screen.getByRole('button', { name: /Batch/i });
    expect(batchBtn).toBeInTheDocument();
    fireEvent.click(batchBtn);

    // Modal should appear
    expect(await screen.findByText(/Batch URL Import/i)).toBeInTheDocument();
    expect(screen.getByText(/Upload \.txt \/ \.csv/i)).toBeInTheDocument();

    // Close the modal
    const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
    fireEvent.click(cancelBtn);

    // Modal should disappear
    await waitFor(() => {
      expect(screen.queryByText(/Batch URL Import/i)).not.toBeInTheDocument();
    });
  });

  it('evaluates rule and displays applied profile badge upon analysis', async () => {
    const mockMedia = {
      url: 'https://www.youtube.com/watch?v=sample123',
      title: 'Automation Rule Tested Video',
      thumbnail: 'https://example.com/thumb.jpg',
      duration: 60,
      duration_string: '01:00',
      uploader: 'Automation Tester',
      webpage_url: 'https://www.youtube.com/watch?v=sample123',
      extractor: 'youtube',
      media_type: 'video',
      video_available: true,
      audio_available: true,
      video_options: [{ label: '1080p', resolution: '1080p', ext: 'mp4', height: 1080, filesize_approx: '50MB' }],
      audio_options: [{ label: 'MP3', format: 'mp3', ext: 'mp3' }],
      supported_containers: ['mp4'],
      technical_summary: { resolution_str: '1080p', media_type: 'video', format_count: 1 },
    };

    const { api } = await import('./services/api');
    vi.mocked(api.analyzeUrl).mockResolvedValueOnce(mockMedia);

    render(<App />);
    const input = screen.getByPlaceholderText(/Paste media link/i);
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=sample123' } });

    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i });
    fireEvent.click(analyzeBtn);

    expect(await screen.findByText('Automation Rule Tested Video')).toBeInTheDocument();
    // Rule badge "Smart Rule Applied: Applied profile: Recommended" should appear
    expect(await screen.findByText(/Smart Rule Applied:/i)).toBeInTheDocument();
    expect(screen.getByText(/Applied profile: Recommended/i)).toBeInTheDocument();
  });
});
