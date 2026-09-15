import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TorrentWorkspace } from './components/TorrentWorkspace';
import { QueueView } from './components/QueueView';
import { UrlInput } from './components/UrlInput';
import { LibraryView } from './components/LibraryView';
import { TorrentMetadataResponse, JobResponse } from './types';
import { api } from './services/api';

vi.mock('./services/api', () => ({
  api: {
    uploadTorrentFile: vi.fn(),
    pauseTorrent: vi.fn().mockResolvedValue({ status: 'ok', job_id: 'torrent-1' }),
    resumeTorrent: vi.fn().mockResolvedValue({ status: 'ok', job_id: 'torrent-1' }),
    recheckTorrent: vi.fn().mockResolvedValue({ status: 'ok', job_id: 'torrent-1' }),
    stopSeeding: vi.fn().mockResolvedValue({ status: 'ok', job_id: 'torrent-1' }),
    getLibrary: vi.fn().mockResolvedValue({
      items: [
        {
          id: 'lib-1',
          title: 'Ubuntu 24.04 Desktop',
          filename: 'ubuntu-24.04-desktop-amd64.iso',
          filesize: 6000000000,
          filesize_formatted: '5.59 GB',
          container: 'iso',
          uploader: 'Canonical',
          source_provider: 'torrent',
          created_at: '2026-09-10T12:00:00Z',
          is_favorite: false,
          is_protected: true,
          download_url: '/api/media/lib-1/download',
          stream_url: '/api/media/lib-1/stream',
        },
        {
          id: 'lib-2',
          title: 'Big Buck Bunny 4K',
          filename: 'big_buck_bunny_4k.mp4',
          filesize: 800000000,
          filesize_formatted: '762 MB',
          container: 'mp4',
          uploader: 'Blender Foundation',
          source_provider: 'ytdlp',
          created_at: '2026-09-10T12:00:00Z',
          is_favorite: true,
          is_protected: false,
          download_url: '/api/media/lib-2/download',
          stream_url: '/api/media/lib-2/stream',
        },
      ],
      total: 2,
      page: 1,
      page_size: 18,
      total_pages: 1,
    }),
    getStorageSummary: vi.fn().mockResolvedValue({
      total_bytes: 6800000000,
      total_formatted: '6.33 GB',
      disk_free_bytes: 120000000000,
      disk_free_formatted: '111.76 GB',
      videos_count: 1,
      audio_count: 0,
      playlists_count: 0,
    }),
    toggleFavorite: vi.fn().mockResolvedValue({ is_favorite: true }),
    toggleProtect: vi.fn().mockResolvedValue({ is_protected: false }),
    deleteMediaItem: vi.fn().mockResolvedValue({ status: 'ok' }),
    setPriority: vi.fn().mockResolvedValue({ status: 'ok' }),
    cancelJob: vi.fn().mockResolvedValue({ status: 'ok' }),
    retryJob: vi.fn().mockResolvedValue({ status: 'ok' }),
    clearCompletedQueue: vi.fn().mockResolvedValue({ status: 'ok' }),
  },
}));

describe('BitTorrent / Magnet Integration Tests', () => {
  const sampleMetadata: TorrentMetadataResponse = {
    info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
    name: 'ubuntu-24.04-desktop-amd64.iso',
    total_size: 6000000000,
    total_size_formatted: '5.59 GB',
    file_count: 3,
    piece_count: 2862,
    piece_length: 2097152,
    is_multi_file: true,
    has_metadata: true,
    files: [
      { index: 0, path: 'ubuntu-24.04-desktop-amd64.iso', size: 6000000000, size_formatted: '5.59 GB', selected: true, priority: 'normal' },
      { index: 1, path: 'checksums.txt', size: 1024, size_formatted: '1 KB', selected: true, priority: 'normal' },
      { index: 2, path: 'preview.mp4', size: 50000000, size_formatted: '47.68 MB', selected: true, priority: 'normal' },
    ],
    comment: 'Ubuntu 24.04 LTS Desktop Image',
    trackers: ['http://torrent.ubuntu.com:6969/announce'],
    magnet_uri: 'magnet:?xt=urn:btih:e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9&dn=ubuntu-24.04-desktop-amd64.iso',
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('detects magnet URI in UrlInput and shows indicator badge', () => {
    const setUrl = vi.fn();
    const onAnalyze = vi.fn();
    const onUploadTorrent = vi.fn();

    render(
      <UrlInput
        url="magnet:?xt=urn:btih:e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9&dn=test"
        setUrl={setUrl}
        onAnalyze={onAnalyze}
        isLoading={false}
        onUploadTorrent={onUploadTorrent}
      />
    );

    expect(screen.getByText(/BitTorrent Magnet URI detected/i)).toBeInTheDocument();
    expect(screen.getByText('Load Torrent')).toBeInTheDocument();
    expect(screen.getByTitle('Upload .torrent file')).toBeInTheDocument();
  });

  it('renders TorrentWorkspace with multi-file table, priorities, and seeding policies', () => {
    const onStartDownload = vi.fn();
    const onReset = vi.fn();

    render(
      <TorrentWorkspace
        metadata={sampleMetadata}
        onStartDownload={onStartDownload}
        isStarting={false}
        onReset={onReset}
      />
    );

    // Verify header and hash
    const nameMatches = screen.getAllByText('ubuntu-24.04-desktop-amd64.iso');
    expect(nameMatches.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9/i)).toBeInTheDocument();

    // Verify files listed
    expect(screen.getByText('checksums.txt')).toBeInTheDocument();
    expect(screen.getByText('preview.mp4')).toBeInTheDocument();

    // Verify seeding policies
    expect(screen.getByText('Stop immediately')).toBeInTheDocument();
    expect(screen.getByText('Ratio 1.0')).toBeInTheDocument();
    expect(screen.getByText('2 Hours')).toBeInTheDocument();

    // Select 1.0x Ratio Seeding Policy
    const ratioOption = screen.getByText('Ratio 1.0');
    fireEvent.click(ratioOption);

    // Click Start Torrent Download
    const startButton = screen.getByText(/Start BitTorrent Download/i);
    fireEvent.click(startButton);

    expect(onStartDownload).toHaveBeenCalledWith(
      expect.objectContaining({
        info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
        seeding_mode: 'ratio_1',
      })
    );
  });

  it('displays live swarm telemetry and control buttons when activeJob is provided to TorrentWorkspace', () => {
    const onStartDownload = vi.fn();
    const activeJob = {
      id: 'job-torrent-live',
      url: sampleMetadata.magnet_uri || 'magnet:?xt=urn:btih:test',
      status: 'DOWNLOADING',
      progress: 68.5,
      provider: 'torrent',
      info_hash: sampleMetadata.info_hash,
      title: sampleMetadata.name,
      torrent_telemetry: {
        info_hash: sampleMetadata.info_hash,
        name: sampleMetadata.name,
        state: 'downloading',
        progress: 68.5,
        download_rate: 15400000,
        upload_rate: 1200000,
        download_rate_human: '14.68 MB/s',
        upload_rate_human: '1.14 MB/s',
        total_downloaded: 4100000000,
        total_uploaded: 500000000,
        num_seeds: 42,
        num_peers: 78,
        total_seeds: 50,
        total_peers: 90,
        ratio: 0.12,
        eta_seconds: 120,
        eta_human: '2m',
        save_path: '/data/downloads/torrents/ubuntu',
        active_duration_seconds: 300,
        seeding_duration_seconds: 0,
        files: [],
      },
    };

    render(
      <TorrentWorkspace
        metadata={sampleMetadata}
        onStartDownload={onStartDownload}
        isStarting={false}
        activeJob={activeJob as unknown as JobResponse}
      />
    );

    // Live Swarm Telemetry Card
    expect(screen.getByText('Live Swarm Telemetry')).toBeInTheDocument();
    expect(screen.getByText('14.68 MB/s')).toBeInTheDocument();
    expect(screen.getByText('1.14 MB/s')).toBeInTheDocument();
    expect(screen.getByText(/42 \(50\) seeds • 78 \(90\) peers/i)).toBeInTheDocument();

    // Pause button in telemetry card
    const pauseBtn = screen.getByText('Pause');
    fireEvent.click(pauseBtn);
    expect(api.pauseTorrent).toHaveBeenCalledWith('job-torrent-live');
  });

  it('displays provider badges and handles pause/resume in QueueView', async () => {
    const onRefresh = vi.fn();
    const jobs = [
      {
        id: 'torrent-job-1',
        url: 'magnet:?xt=urn:btih:123',
        title: 'Linux Mint 22 Torrent',
        status: 'DOWNLOADING',
        progress: 45,
        provider: 'torrent',
        speed: '8.5 MB/s',
        eta: '3m',
      },
      {
        id: 'ytdlp-job-2',
        url: 'https://youtube.com/watch?v=abc',
        title: 'YouTube Video Extraction',
        status: 'DOWNLOADING',
        progress: 80,
        provider: 'ytdlp',
        speed: '12 MB/s',
        eta: '20s',
      },
    ];

    render(<QueueView jobs={jobs as unknown as JobResponse[]} onRefresh={onRefresh} />);

    // Verify TORRENT and YT-DLP badges
    expect(screen.getByText('TORRENT')).toBeInTheDocument();
    expect(screen.getByText('YT-DLP')).toBeInTheDocument();

    // Verify Pause button is rendered for downloading torrent
    const pauseButton = screen.getByTitle('Pause Torrent');
    fireEvent.click(pauseButton);
    expect(api.pauseTorrent).toHaveBeenCalledWith('torrent-job-1');
  });

  it('filters by source provider and displays Torrent badge in LibraryView', async () => {
    render(<LibraryView />);

    await waitFor(() => {
      expect(screen.getByText('Ubuntu 24.04 Desktop')).toBeInTheDocument();
      expect(screen.getByText('Big Buck Bunny 4K')).toBeInTheDocument();
    });

    // Verify Torrent badge on Ubuntu card
    expect(screen.getByText('Torrent')).toBeInTheDocument();

    // Change provider filter to "Torrent Only"
    const providerSelect = screen.getByDisplayValue('All Sources');
    fireEvent.change(providerSelect, { target: { value: 'torrent' } });

    await waitFor(() => {
      expect(api.getLibrary).toHaveBeenCalledWith(
        expect.objectContaining({
          provider: 'torrent',
        })
      );
    });
  });
});
