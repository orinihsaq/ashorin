import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TorrentWorkspace } from './components/TorrentWorkspace';
import { TorrentMetadataResponse, JobResponse } from './types';

const mockMetadata: TorrentMetadataResponse = {
  info_hash: 'abcdef1234567890abcdef1234567890abcdef12',
  name: 'Sample Torrent Workspace Package',
  total_size: 1572864000,
  total_size_formatted: '1.46 GB',
  file_count: 5,
  piece_count: 750,
  piece_length: 2097152,
  trackers: ['udp://tracker.openbittorrent.com:6969/announce', 'udp://tracker.opentrackr.org:1337/announce'],
  is_multi_file: true,
  has_metadata: true,
  magnet_uri: 'magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12&dn=Sample+Torrent',
  files: [
    {
      index: 0,
      path: 'Movies/FeatureFilm.mkv',
      size: 1048576000,
      size_formatted: '1000 MB',
      selected: true,
      priority: 'normal',
    },
    {
      index: 1,
      path: 'Movies/Subtitles.srt',
      size: 51200,
      size_formatted: '50 KB',
      selected: true,
      priority: 'normal',
    },
    {
      index: 2,
      path: 'Soundtrack/AudioTrack.flac',
      size: 314572800,
      size_formatted: '300 MB',
      selected: true,
      priority: 'normal',
    },
    {
      index: 3,
      path: 'Documents/Manual.pdf',
      size: 209715200,
      size_formatted: '200 MB',
      selected: true,
      priority: 'normal',
    },
    {
      index: 4,
      path: 'Archives/Extras.zip',
      size: 5242880,
      size_formatted: '5 MB',
      selected: true,
      priority: 'normal',
    },
  ],
};

describe('TorrentWorkspace Premium UI Tests', () => {
  it('renders hero card with info hash, swarm size, and magnet badge', () => {
    render(
      <TorrentWorkspace
        metadata={mockMetadata}
        onStartDownload={vi.fn()}
        isStarting={false}
      />
    );

    expect(screen.getByText('Sample Torrent Workspace Package')).toBeInTheDocument();
    expect(screen.getByText('MAGNET')).toBeInTheDocument();
    expect(screen.getByText('1.46 GB')).toBeInTheDocument();
    expect(screen.getByText('abcdef1234567890abcdef1234567890abcdef12')).toBeInTheDocument();
    expect(screen.getByText(/2 trackers/i)).toBeInTheDocument();
  });

  it('filters files by category tabs and search input', () => {
    render(
      <TorrentWorkspace
        metadata={mockMetadata}
        onStartDownload={vi.fn()}
        isStarting={false}
      />
    );

    // Filter tabs exist
    expect(screen.getAllByText('All').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Video')).toBeInTheDocument();
    expect(screen.getByText('Audio')).toBeInTheDocument();
    expect(screen.getByText('Docs')).toBeInTheDocument();
    expect(screen.getAllByText('Archives').length).toBeGreaterThanOrEqual(1);

    // Click Video tab
    fireEvent.click(screen.getByText('Video'));
    expect(screen.getByText('Movies')).toBeInTheDocument();

    // Search input
    const searchInput = screen.getByPlaceholderText('Search files…');
    fireEvent.change(searchInput, { target: { value: 'Audio' } });
    // Switch back to All tab
    const allTabs = screen.getAllByText('All');
    fireEvent.click(allTabs[allTabs.length - 1]);
    expect(screen.getByText('Soundtrack')).toBeInTheDocument();
  });

  it('supports folder toggle and quick selection actions', () => {
    const onStartDownload = vi.fn();
    render(
      <TorrentWorkspace
        metadata={mockMetadata}
        onStartDownload={onStartDownload}
        isStarting={false}
      />
    );

    // Click None to deselect all
    fireEvent.click(screen.getByText('None'));
    expect(screen.getByText(/of 5 files selected/i)).toBeInTheDocument();

    // Click All in toolbar (first one)
    const allButtons = screen.getAllByText('All');
    fireEvent.click(allButtons[0]);
    expect(screen.getByText(/of 5 files selected/i)).toBeInTheDocument();

    // Click Invert
    fireEvent.click(screen.getByText('Invert'));
    expect(screen.getByText(/of 5 files selected/i)).toBeInTheDocument();

    // Click Media Only
    fireEvent.click(screen.getByText('Media Only'));
    expect(screen.getByText(/of 5 files selected/i)).toBeInTheDocument();
  });

  it('configures destination folder and seeding policy', () => {
    const onStartDownload = vi.fn();
    render(
      <TorrentWorkspace
        metadata={mockMetadata}
        onStartDownload={onStartDownload}
        isStarting={false}
      />
    );

    // Check seeding policies
    expect(screen.getByText('Stop immediately')).toBeInTheDocument();
    expect(screen.getByText('Ratio 1.0')).toBeInTheDocument();
    expect(screen.getByText('Ratio 2.0')).toBeInTheDocument();
    expect(screen.getByText('30 Minutes')).toBeInTheDocument();
    expect(screen.getByText('2 Hours')).toBeInTheDocument();
    expect(screen.getByText('Indefinitely')).toBeInTheDocument();

    // Select Ratio 2.0
    fireEvent.click(screen.getByText('Ratio 2.0'));

    // Change destination folder
    const destInput = screen.getByPlaceholderText('Folder name');
    fireEvent.change(destInput, { target: { value: 'CustomMediaFolder' } });

    // Click start download
    const startBtn = screen.getByText(/Start BitTorrent Download/i);
    fireEvent.click(startBtn);

    expect(onStartDownload).toHaveBeenCalledWith(
      expect.objectContaining({
        destination_folder: 'CustomMediaFolder',
        seeding_mode: 'ratio_2',
      })
    );
  });

  it('renders completed state with archive download button', () => {
    const completedJob = {
      id: 'completed-torrent-job',
      title: 'Sample Torrent Workspace Package',
      output_filename: 'Sample Torrent Workspace Package.zip',
      status: 'COMPLETED',
      progress: 100,
      provider: 'torrent',
      output_type: 'directory',
      file_count: 5,
      torrent_telemetry: {
        info_hash: mockMetadata.info_hash,
        name: mockMetadata.name,
        ratio: 1.45,
      },
    } as unknown as JobResponse;

    const onReset = vi.fn();
    render(
      <TorrentWorkspace
        metadata={mockMetadata}
        onStartDownload={vi.fn()}
        isStarting={false}
        activeJob={completedJob}
        onReset={onReset}
      />
    );

    expect(screen.getByText('Torrent Download Complete')).toBeInTheDocument();
    expect(screen.getByText(/Download Archive \(\.zip\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Ratio: 1.45×/i)).toBeInTheDocument();
    expect(screen.getByText('New Download')).toBeInTheDocument();

    fireEvent.click(screen.getByText('New Download'));
    expect(onReset).toHaveBeenCalled();
  });

  it('does NOT show connecting to DHT swarm text once metadata phase is received', () => {
    const pendingMeta: TorrentMetadataResponse = {
      info_hash: '1111111111222222222233333333334444444444',
      name: 'Pending Swarm Torrent',
      total_size: 0,
      total_size_formatted: '0 B',
      file_count: 0,
      piece_count: 0,
      piece_length: 0,
      trackers: [],
      is_multi_file: false,
      has_metadata: false,
      magnet_uri: 'magnet:?xt=urn:btih:1111111111222222222233333333334444444444',
      files: [],
    };

    const jobWithMetadataReceived = {
      id: 'job-123',
      url: 'magnet:?xt=urn:btih:1111111111222222222233333333334444444444',
      status: 'ACQUIRING_METADATA',
      progress: 0,
      provider: 'torrent',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      torrent_telemetry: {
        peers: 5,
        trackers_contacted: 5,
        dht_active: true,
        metadata_phase: 'Metadata received',
      },
    } as unknown as JobResponse;

    render(
      <TorrentWorkspace
        metadata={pendingMeta}
        activeJob={jobWithMetadataReceived}
        onStartDownload={vi.fn()}
        isStarting={false}
        onReset={vi.fn()}
      />
    );

    // Contradictory text should NOT be present
    expect(
      screen.queryByText(/Connecting to DHT nodes and peer swarm to retrieve file manifest and total size/i)
    ).not.toBeInTheDocument();

    // Transition title should be informative
    expect(screen.getByText(/Metadata received · Preparing file selection\.\.\./i)).toBeInTheDocument();
  });

  it('renders file manifest immediately when activeJob has metadata, even if prop metadata was pending shell', () => {
    const pendingMeta: TorrentMetadataResponse = {
      info_hash: mockMetadata.info_hash,
      name: 'Pending Swarm Torrent',
      total_size: 0,
      total_size_formatted: '0 B',
      file_count: 0,
      piece_count: 0,
      piece_length: 0,
      trackers: [],
      is_multi_file: false,
      has_metadata: false,
      files: [],
    };

    const jobWithFullMetadata = {
      id: 'job-456',
      url: 'magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12',
      status: 'WAITING_FOR_SELECTION',
      progress: 0,
      provider: 'torrent',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      torrent_info: mockMetadata,
      torrent_telemetry: {
        peers: 0,
        trackers_contacted: 0,
        dht_active: false,
        metadata_phase: 'Metadata received',
      },
    } as unknown as JobResponse;

    render(
      <TorrentWorkspace
        metadata={pendingMeta}
        activeJob={jobWithFullMetadata}
        onStartDownload={vi.fn()}
        isStarting={false}
        onReset={vi.fn()}
      />
    );

    // Acquisition card is hidden
    expect(screen.queryByText(/Acquiring torrent metadata/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Metadata received · Preparing/i)).not.toBeInTheDocument();

    // File selection browser must be visible with files
    expect(screen.getByText('File Selection')).toBeInTheDocument();
    expect(screen.getByText('Movies')).toBeInTheDocument();
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText(/of 5 files selected/i)).toBeInTheDocument();
  });

  it('displays manifest regardless of 0 peers or inactive DHT once metadata exists', () => {
    const jobZeroPeers = {
      id: 'job-789',
      url: 'magnet:?xt=urn:btih:abcdef1234567890abcdef1234567890abcdef12',
      status: 'WAITING_FOR_SELECTION',
      progress: 0,
      provider: 'torrent',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      torrent_info: mockMetadata,
      torrent_telemetry: {
        peers: 0,
        dht_active: false,
        trackers_contacted: 0,
        metadata_phase: 'Metadata received',
      },
    } as unknown as JobResponse;

    render(
      <TorrentWorkspace
        metadata={mockMetadata}
        activeJob={jobZeroPeers}
        onStartDownload={vi.fn()}
        isStarting={false}
        onReset={vi.fn()}
      />
    );

    expect(screen.getByText('File Selection')).toBeInTheDocument();
    expect(screen.getByText('Movies')).toBeInTheDocument();
    expect(screen.getByText(/Start BitTorrent Download/i)).toBeInTheDocument();
  });
});

