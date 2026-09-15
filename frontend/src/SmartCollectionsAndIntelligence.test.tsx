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
      {
        id: 'music',
        name: 'Music',
        description: 'Audio-only FLAC/MP3 extraction',
        profile_id: 'music',
        storage_folder: 'Music/{title}',
        duplicate_policy: 'skip',
        target_quality: '320k',
        minimum_quality: '128k',
        upgrade_policy: 'upgrade_if_better',
        retention_days: 0,
        notify_events: ['download_completed'],
        is_builtin: true,
        is_default: false,
        created_at: 1700000000,
        updated_at: 1700000000,
      },
    ]),
    getWatchers: vi.fn().mockResolvedValue([
      {
        id: 'watch-1',
        name: 'Tech Channel Feed',
        source_url: 'https://youtube.com/playlist?list=PL12345',
        schedule: 'every_6_hours',
        profile_id: 'recommended',
        target_quality: '1080p',
        download_new: true,
        status: 'active',
        last_sync_at: 1700000000,
        next_sync_at: 1700021600,
        items_fetched: 25,
        items_downloaded: 10,
        created_at: 1700000000,
        updated_at: 1700000000,
      },
    ]),
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
      title: 'Sample Preflight Video',
      is_playlist: false,
      total_items: 1,
      selected_items: 1,
      new_items_count: 1,
      existing_items_count: 0,
      upgrade_items_count: 0,
      unavailable_items_count: 0,
      estimated_total_bytes: 25000000,
      estimated_total_formatted: '25.0 MB',
      disk_free_bytes: 150000000000,
      disk_free_formatted: '139.7 GB',
      storage_status: 'sufficient',
      storage_message: 'Adequate disk space',
      resolved_profile_id: 'recommended',
      resolved_profile_name: 'Recommended',
      destination_folder: '/downloads',
      items: [
        {
          index: 1,
          title: 'Sample Preflight Video',
          url: 'https://example.com/watch?v=sample123',
          status: 'new',
          estimated_bytes_formatted: '25.0 MB',
        },
      ],
      explanations: ['Safe to queue download.'],
    }),
    analyzeUrl: vi.fn(),
    startDownload: vi.fn(),
    cancelJob: vi.fn(),
    deleteJob: vi.fn(),
    updateYtDlp: vi.fn(),
  },
}));

describe('ashoriN Smart Collections, Sync & Media Intelligence', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Watchers tab and navigates to Collection Watchers view', async () => {
    render(<App />);

    // Watchers navigation tab
    const watchersTabs = screen.getAllByRole('button', { name: /Watchers/i });
    expect(watchersTabs.length).toBeGreaterThan(0);

    fireEvent.click(watchersTabs[0]);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Collection Watchers/i })).toBeInTheDocument();
      expect(screen.getByText(/Tech Channel Feed/i)).toBeInTheDocument();
    });
  });

  it('renders Health tab and navigates to Media Health Center view', async () => {
    render(<App />);

    const healthTabs = screen.getAllByRole('button', { name: /Health/i });
    expect(healthTabs.length).toBeGreaterThan(0);

    fireEvent.click(healthTabs[0]);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Media Health Center/i })).toBeInTheDocument();
      expect(screen.getByText(/Non-Destructive Guarantee/i)).toBeInTheDocument();
      expect(screen.getByText(/Storage Capacity & Ingestion Forecast/i)).toBeInTheDocument();
    });
  });

  it('opens and closes the Workflow Recipe modal from the home activity bar', async () => {
    render(<App />);

    // Click on Workflow in the home quick activity summary bar
    const workflowBtn = screen.getByRole('button', { name: /Workflow/i });
    fireEvent.click(workflowBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Download Recipes/i })).toBeInTheDocument();
      expect(screen.getByText(/Best video and audio merged/i)).toBeInTheDocument();
      expect(screen.getByText(/Audio-only FLAC\/MP3 extraction/i)).toBeInTheDocument();
    });

    // Close modal
    const closeBtns = screen.getAllByRole('button');
    const xBtn = closeBtns.find((b) => b.querySelector('svg'));
    if (xBtn) fireEvent.click(xBtn);
  });
});
