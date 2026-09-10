import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';

// Mock the API calls
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
    analyzeUrl: vi.fn(),
    startDownload: vi.fn(),
    cancelJob: vi.fn(),
    deleteJob: vi.fn(),
    updateYtDlp: vi.fn(),
  },
}));

describe('ashoriN App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ashoriN brand heading, badge, and description', () => {
    render(<App />);
    expect(screen.getAllByText(/PRECISION MEDIA EXTRACTION/i).length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getByText(/High-performance self-hosted media extraction engine/i)
    ).toBeInTheDocument();
  });

  it('renders required footer dedication and stack attribution', () => {
    render(<App />);
    expect(screen.getByText(/Made in Love with her ♥/i)).toBeInTheDocument();
    expect(screen.getByText(/Powered by yt-dlp \+ FFmpeg/i)).toBeInTheDocument();
  });

  it('renders URL input with correct placeholder and submit button', () => {
    render(<App />);
    const input = screen.getByPlaceholderText(/Paste media link/i);
    expect(input).toBeInTheDocument();

    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i });
    expect(analyzeBtn).toBeInTheDocument();
    expect(analyzeBtn).toBeDisabled();
  });

  it('enables analyze button when URL is entered', () => {
    render(<App />);
    const input = screen.getByPlaceholderText(/Paste media link/i);
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=123' } });

    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i });
    expect(analyzeBtn).not.toBeDisabled();
  });

  it('renders sample quick-test buttons', () => {
    render(<App />);
    expect(screen.getByText(/Big Buck Bunny \(YouTube 4K\)/i)).toBeInTheDocument();
    expect(screen.getByText(/W3C Sample Clip \(Direct MP4\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Archive.org Open Media/i)).toBeInTheDocument();
  });

  it('handles media analysis and allows switching between Recommended and Advanced yt-dlp mode', async () => {
    const mockMedia = {
      url: 'https://www.youtube.com/watch?v=123',
      title: 'Sample Video 4K Test',
      thumbnail: 'https://example.com/thumb.jpg',
      duration: 120,
      duration_string: '02:00',
      uploader: 'Demo Creator',
      webpage_url: 'https://www.youtube.com/watch?v=123',
      extractor: 'youtube',
      media_type: 'video',
      video_available: true,
      audio_available: true,
      video_options: [
        { label: '1080p (Full HD)', resolution: '1080p', height: 1080, filesize_approx: '50MB', ext: 'mp4' },
      ],
      audio_options: [
        { label: 'MP3 Audio', format: 'mp3', ext: 'mp3' },
      ],
      supported_containers: ['mp4', 'mkv', 'webm'],
      technical_summary: {
        resolution_str: '1920x1080',
        fps: 60,
        vcodec: 'avc1',
        acodec: 'mp4a',
        tbr: 4500,
        format_count: 8,
        media_type: 'video',
      },
    };

    const { api } = await import('./services/api');
    vi.mocked(api.analyzeUrl).mockResolvedValueOnce(mockMedia);

    render(<App />);
    const input = screen.getByPlaceholderText(/Paste media link/i);
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=123' } });

    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i });
    fireEvent.click(analyzeBtn);

    // Should display media title and workspace
    expect(await screen.findByText('Sample Video 4K Test')).toBeInTheDocument();
    expect(screen.getByText('Demo Creator')).toBeInTheDocument();

    // Recommended mode should be active by default
    expect(screen.getByText('Optimization Presets')).toBeInTheDocument();
    expect(screen.getByText('Select Video Resolution')).toBeInTheDocument();

    // Toggle to Advanced yt-dlp mode
    const advTab = screen.getByRole('button', { name: /Advanced yt-dlp/i });
    fireEvent.click(advTab);

    // Advanced sections should now be visible
    expect(screen.getByText(/General & Output/i)).toBeInTheDocument();
    expect(screen.getByText(/Custom Output Filename Template/i)).toBeInTheDocument();
  });
});

