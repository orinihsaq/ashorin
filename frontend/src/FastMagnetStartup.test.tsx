import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { UrlInput } from './components/UrlInput';
import { TorrentWorkspace } from './components/TorrentWorkspace';
import { DownloadProgress } from './components/DownloadProgress';
import { JobResponse, TorrentMetadataResponse } from './types';

const createMockJob = (overrides: Partial<JobResponse> = {}): JobResponse => ({
  id: 'mock-job-1',
  url: 'magnet:?xt=urn:btih:e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
  title: 'ubuntu-24.04',
  thumbnail: null,
  status: 'ACQUIRING_METADATA',
  progress: 0,
  speed: null,
  eta: null,
  current_stage: 'Waiting for torrent metadata...',
  downloaded_bytes: 0,
  total_bytes: null,
  created_at: Date.now(),
  started_at: null,
  completed_at: null,
  output_filename: null,
  error_message: null,
  is_playlist: false,
  playlist_title: null,
  total_items: 0,
  completed_items: 0,
  provider: 'torrent',
  input_type: 'magnet',
  info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
  ...overrides,
} as JobResponse);

describe('Fast Magnet Startup & Non-Blocking Workflow Tests', () => {
  it('renders immediate background actions in UrlInput when magnet link is entered', () => {
    const setUrl = vi.fn();
    const onAnalyze = vi.fn();
    const onFastQueueTorrent = vi.fn();
    const magnet = 'magnet:?xt=urn:btih:e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9&dn=Ubuntu';

    render(
      <UrlInput
        url={magnet}
        setUrl={setUrl}
        onAnalyze={onAnalyze}
        isLoading={false}
        onFastQueueTorrent={onFastQueueTorrent}
      />
    );

    expect(screen.getByText('Torrent detected')).toBeInTheDocument();
    expect(screen.getByText(/Metadata is being retrieved in the background/i)).toBeInTheDocument();
    const startBgBtn = screen.getByText('Start in background');
    const queueBtn = screen.getByText('Queue torrent');
    expect(startBgBtn).toBeInTheDocument();
    expect(queueBtn).toBeInTheDocument();

    fireEvent.click(startBgBtn);
    expect(onFastQueueTorrent).toHaveBeenCalledWith(magnet);
  });

  it('renders State 1 in TorrentWorkspace when metadata is pending with enabled start in background', () => {
    const onStartDownload = vi.fn();
    const pendingMetadata: TorrentMetadataResponse = {
      info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
      name: 'ubuntu-24.04',
      total_size: 0,
      total_size_formatted: 'Unknown',
      file_count: 0,
      piece_count: 0,
      piece_length: 0,
      trackers: ['udp://tracker.opentrackr.org:1337/announce'],
      is_multi_file: false,
      files: [],
      has_metadata: false,
      magnet_uri: 'magnet:?xt=urn:btih:e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
    };

    render(
      <TorrentWorkspace
        metadata={pendingMetadata}
        onStartDownload={onStartDownload}
        isStarting={false}
      />
    );

    expect(screen.getAllByText(/Metadata is being retrieved in the background/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Safe default policy: all files will be automatically downloaded/i)).toBeInTheDocument();

    // Start in background buttons must be clickable and enabled
    const bgButtons = screen.getAllByText(/Start in Background/i);
    expect(bgButtons.length).toBeGreaterThan(0);
    fireEvent.click(bgButtons[0]);
    expect(onStartDownload).toHaveBeenCalledWith(
      expect.objectContaining({
        info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
        selected_indices: null,
      })
    );
  });

  it('renders ACQUIRING_METADATA discovery card with live telemetry and notice in DownloadProgress', () => {
    const onCancel = vi.fn();
    const onReset = vi.fn();

    const job = createMockJob({
      id: 'job-meta-123',
      status: 'ACQUIRING_METADATA',
      torrent_telemetry: {
        info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
        name: 'ubuntu-24.04',
        ratio: 0,
        trackers_contacted: 4,
        peers: 7,
        dht_active: true,
        metadata_phase: 'Connecting to swarm',
      },
    });

    render(
      <DownloadProgress
        job={job}
        onCancel={onCancel}
        onReset={onReset}
      />
    );

    expect(screen.getByText('Retrieving Torrent Metadata')).toBeInTheDocument();
    expect(screen.getByText('4 Contacted')).toBeInTheDocument();
    expect(screen.getByText('7 Discovered')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText(/You can safely close or navigate away/i)).toBeInTheDocument();
  });

  it('renders READY status with Start Download action in DownloadProgress', () => {
    const onCancel = vi.fn();
    const onReset = vi.fn();
    const onStartJob = vi.fn();

    const job = createMockJob({
      id: 'job-ready-123',
      status: 'READY',
      torrent_telemetry: {
        info_hash: 'e23a31c5b8b9393e96f1b34c1b9df52cfa8a65c9',
        name: 'ubuntu-24.04',
        ratio: 0,
        file_count: 3,
        total_size_formatted: '2.5 GB',
      },
    });

    render(
      <DownloadProgress
        job={job}
        onCancel={onCancel}
        onReset={onReset}
        onStartJob={onStartJob}
      />
    );

    expect(screen.getByText('Torrent Metadata Retrieved & Ready')).toBeInTheDocument();
    const startBtn = screen.getByText('Start Download');
    expect(startBtn).toBeInTheDocument();
    fireEvent.click(startBtn);
    expect(onStartJob).toHaveBeenCalledWith('job-ready-123');
  });

  it('renders METADATA_FAILED with Retry action in DownloadProgress', () => {
    const onCancel = vi.fn();
    const onReset = vi.fn();
    const onRetryJob = vi.fn();

    const job = createMockJob({
      id: 'job-fail-123',
      status: 'METADATA_FAILED',
      error_message: 'Timed out waiting for BitTorrent metadata after 180s',
    });

    render(
      <DownloadProgress
        job={job}
        onCancel={onCancel}
        onReset={onReset}
        onRetryJob={onRetryJob}
      />
    );

    expect(screen.getByText('Metadata Acquisition Timed Out')).toBeInTheDocument();
    const retryBtn = screen.getByText('Retry Discovery');
    expect(retryBtn).toBeInTheDocument();
    fireEvent.click(retryBtn);
    expect(onRetryJob).toHaveBeenCalledWith('job-fail-123');
  });
});
