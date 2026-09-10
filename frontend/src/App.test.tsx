import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from './App';

// Mock the API calls
vi.mock('./services/api', () => ({
  api: {
    getSystemInfo: vi.fn().mockResolvedValue({
      app_name: 'Media Downloader Pro',
      app_version: '1.0.0',
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

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders application title and description', () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 2, name: /Media Downloader/i })).toBeInTheDocument();
    expect(
      screen.getByText(/Download media from supported websites with selectable resolutions/i)
    ).toBeInTheDocument();
  });

  it('renders URL input with correct placeholder and submit button', () => {
    render(<App />);
    const input = screen.getByPlaceholderText(/Paste video or audio link/i);
    expect(input).toBeInTheDocument();

    const analyzeBtn = screen.getByRole('button', { name: /Analyze/i });
    expect(analyzeBtn).toBeInTheDocument();
    expect(analyzeBtn).toBeDisabled();
  });

  it('enables analyze button when URL is entered', () => {
    render(<App />);
    const input = screen.getByPlaceholderText(/Paste video or audio link/i);
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
});
