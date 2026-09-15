import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from './App';
import { Header } from './components/Header';

vi.mock('./services/api', () => ({
  api: {
    getHealth: vi.fn().mockResolvedValue({
      status: 'ok',
      version: '2.5.0',
      yt_dlp_version: '2026.03.01',
      ffmpeg_installed: true,
      downloads_path: '/app/downloads',
      disk_usage: {
        total_bytes: 107374182400,
        used_bytes: 21474836480,
        free_bytes: 85899345920,
        total_formatted: '100.0 GB',
        used_formatted: '20.0 GB',
        free_formatted: '80.0 GB',
        percent_used: 20.0,
      },
    }),
    analyzeMedia: vi.fn(),
    getQueue: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    getLibrary: vi.fn().mockResolvedValue({ items: [], total: 0, total_pages: 1 }),
    getStorageSummary: vi.fn().mockResolvedValue({
      total_bytes: 0,
      total_formatted: '0 B',
      videos_count: 0,
      audio_count: 0,
      playlists_count: 0,
      disk_free_bytes: 85899345920,
      disk_free_formatted: '80.0 GB',
    }),
    getWatchers: vi.fn().mockResolvedValue([]),
    getProfiles: vi.fn().mockResolvedValue([]),
    getRecipes: vi.fn().mockResolvedValue([]),
    getLatestHealthScan: vi.fn().mockResolvedValue(null),
    getStorageForecast: vi.fn().mockResolvedValue(null),
    getStatistics: vi.fn().mockResolvedValue({
      total_downloads: 0,
      completed_downloads: 0,
      failed_downloads: 0,
      total_bytes: 0,
      total_formatted: '0 B',
      active_downloads: 0,
      queued_downloads: 0,
      downloads_by_day: [],
      top_extractors: [],
      top_containers: [],
    }),
    getSettings: vi.fn().mockResolvedValue({
      retention_enabled: false,
      retention_days: 7,
      max_concurrent_downloads: 3,
      default_quality: '1080p',
      default_folder: 'ashoriN_Media',
      webhook_enabled: false,
      webhook_url: '',
    }),
    getRules: vi.fn().mockResolvedValue([]),
    getApiKeys: vi.fn().mockResolvedValue([]),
    getWebhooks: vi.fn().mockResolvedValue([]),
  },
}));

describe('Responsive Design & Architecture Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders fixed mobile bottom navigation with core destinations', async () => {
    render(<App />);

    const mobileNav = screen.getByRole('navigation', { name: /mobile navigation/i });
    expect(mobileNav).toBeInTheDocument();

    expect(screen.getByRole('button', { name: /open more navigation/i })).toBeInTheDocument();
  });

  it('opens mobile slide-over sheet when More button is clicked and closes it', async () => {
    render(<App />);

    const moreButton = screen.getByRole('button', { name: /open more navigation/i });
    fireEvent.click(moreButton);

    // Slide-over drawer should appear
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /close navigation/i })).toBeInTheDocument();
      expect(screen.getAllByText(/watchers/i).length).toBeGreaterThan(0);
    });

    // Clicking close button dismisses sheet
    const closeBtn = screen.getByRole('button', { name: /close navigation/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /close navigation/i })).not.toBeInTheDocument();
    });
  });

  it('navigates to secondary views from mobile sheet and closes sheet', async () => {
    render(<App />);

    const moreButton = screen.getByRole('button', { name: /open more navigation/i });
    fireEvent.click(moreButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /close navigation/i })).toBeInTheDocument();
    });

    // In the drawer, find button for watchers
    const watcherButtons = screen.getAllByRole('button').filter(b => b.textContent?.includes('Watchers'));
    expect(watcherButtons.length).toBeGreaterThan(0);
    fireEvent.click(watcherButtons[0]);

    // Should switch view and close menu
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /close navigation/i })).not.toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /collection/i })).toBeInTheDocument();
    });
  });

  it('renders tablet compact navigation with More popover trigger', () => {
    const onChangeView = vi.fn();
    render(
      <Header
        theme="dark"
        onToggleTheme={() => {}}
        onOpenSystemInfo={() => {}}
        onToggleHistory={() => {}}
        historyCount={0}
        systemInfo={null}
        activeView="home"
        onChangeView={onChangeView}
      />
    );

    // Tablet dropdown button
    const tabletMoreBtn = screen.getByRole('button', { name: /more navigation options/i });
    expect(tabletMoreBtn).toBeInTheDocument();

    fireEvent.click(tabletMoreBtn);

    // Dropdown popover menu appears with secondary destinations
    expect(screen.getAllByText(/watchers/i).length).toBeGreaterThan(0);
  });
});
