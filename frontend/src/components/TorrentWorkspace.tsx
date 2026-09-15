import React, { useState, useMemo, useCallback, useEffect } from 'react';
import {
  DownloadSimple,
  Magnet,
  FolderOpen,
  CheckSquare,
  Square,
  ArrowsLeftRight,
  Video,
  MusicNotes,
  FileText,
  File,
  Pause,
  Play,
  ArrowClockwise,
  StopCircle,
  XCircle,
  Copy,
  Check,
  HardDrives,
  Speedometer,
  Users,
  ArrowsDownUp,
  CircleNotch,
  Broadcast,
  WarningCircle,
  Lightning,
  Archive,
  CaretRight,
  CaretDown,
  CheckCircle,
  Folder,
} from '@phosphor-icons/react';
import { TorrentMetadataResponse, TorrentDownloadConfig, JobResponse, TorrentFileItem } from '../types';
import { api } from '../services/api';

// ─── Tree Data Structures ────────────────────────────────────────────────────

interface FileNode {
  type: 'file';
  name: string;
  path: string;
  size: number;
  file: TorrentFileItem;
}

interface FolderNode {
  type: 'folder';
  name: string;
  path: string;
  size: number;
  children: TreeNode[];
}

type TreeNode = FileNode | FolderNode;

function buildTree(files: TorrentFileItem[]): TreeNode[] {
  const root: TreeNode[] = [];
  const map = new Map<string, FolderNode>();

  files.forEach((file) => {
    const parts = file.path.split('/');

    let currentPath = '';
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLeaf = i === parts.length - 1;
      const parentPath = currentPath;
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (!map.has(currentPath)) {
        if (isLeaf) {
          const fileNode: FileNode = {
            type: 'file',
            name: part,
            path: currentPath,
            size: file.size,
            file,
          };
          if (parentPath) {
            map.get(parentPath)!.children.push(fileNode);
          } else {
            root.push(fileNode);
          }
        } else {
          const folderNode: FolderNode = {
            type: 'folder',
            name: part,
            path: currentPath,
            size: 0,
            children: [],
          };
          map.set(currentPath, folderNode);
          if (parentPath) {
            map.get(parentPath)!.children.push(folderNode);
          } else {
            root.push(folderNode);
          }
        }
      }

      // Accumulate size up through folder ancestors
      if (!isLeaf) {
        map.get(currentPath)!.size += file.size;
      }
    }
  });

  const sortNodes = (nodes: TreeNode[]) => {
    nodes.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
    nodes.forEach((n) => {
      if (n.type === 'folder') sortNodes(n.children);
    });
  };
  sortNodes(root);
  return root;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const formatSize = (b: number): string => {
  if (b === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return parseFloat((b / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

type FileCategory = 'all' | 'video' | 'audio' | 'documents' | 'archives' | 'other';

const VIDEO_EXTS = new Set(['.mp4', '.mkv', '.webm', '.avi', '.mov', '.m4v', '.ts', '.wmv']);
const AUDIO_EXTS = new Set(['.mp3', '.flac', '.m4a', '.wav', '.ogg', '.opus', '.aac']);
const DOC_EXTS = new Set(['.txt', '.nfo', '.md', '.srt', '.vtt', '.pdf', '.doc', '.docx', '.sub']);
const ARCHIVE_EXTS = new Set(['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']);

function getFileCategory(path: string): FileCategory {
  const ext = '.' + path.split('.').pop()?.toLowerCase();
  if (VIDEO_EXTS.has(ext)) return 'video';
  if (AUDIO_EXTS.has(ext)) return 'audio';
  if (DOC_EXTS.has(ext)) return 'documents';
  if (ARCHIVE_EXTS.has(ext)) return 'archives';
  return 'other';
}

function getFileIcon(path: string): React.ReactElement {
  const cat = getFileCategory(path);
  if (cat === 'video') return <Video size={15} className="text-purple-400 shrink-0" />;
  if (cat === 'audio') return <MusicNotes size={15} className="text-purple-300 shrink-0" />;
  if (cat === 'documents') return <FileText size={15} className="text-zinc-400 shrink-0" />;
  if (cat === 'archives') return <Archive size={15} className="text-zinc-500 shrink-0" />;
  return <File size={15} className="text-zinc-500 shrink-0" />;
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface TorrentWorkspaceProps {
  metadata: TorrentMetadataResponse;
  onStartDownload: (config: TorrentDownloadConfig) => void;
  isStarting: boolean;
  onReset?: () => void;
  activeJob?: JobResponse | null;
  onPause?: (jobId: string) => void;
  onResume?: (jobId: string) => void;
  onRecheck?: (jobId: string) => void;
  onStopSeeding?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
  onCancelJob?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface StatePillProps {
  status: string | undefined;
  hasMeta: boolean;
}
const StatePill: React.FC<StatePillProps> = ({ status, hasMeta }) => {
  if (!status) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-zinc-700">
        {hasMeta ? 'READY' : 'DETECTING'}
      </span>
    );
  }
  const cls =
    status === 'COMPLETED'
      ? 'bg-purple-950/60 text-purple-200 border-purple-800/60'
      : status === 'SEEDING'
      ? 'bg-purple-900/40 text-purple-300 border-purple-700/50'
      : status === 'PAUSED'
      ? 'bg-zinc-800/80 text-zinc-400 border-zinc-700'
      : status === 'FAILED' || status === 'METADATA_FAILED'
      ? 'bg-zinc-900/60 text-zinc-400 border-zinc-700'
      : status === 'WAITING_FOR_METADATA' || status === 'ACQUIRING_METADATA'
      ? 'bg-purple-900/30 text-purple-400 border-purple-800/40 animate-pulse'
      : status === 'WAITING_FOR_SELECTION' || status === 'READY'
      ? 'bg-indigo-900/40 text-indigo-300 border-indigo-700/50'
      : 'bg-purple-500/20 text-purple-300 border-purple-500/30';
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${cls}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
};

// ─── Main Component ───────────────────────────────────────────────────────────

export const TorrentWorkspace: React.FC<TorrentWorkspaceProps> = ({
  metadata: propMetadata,
  onStartDownload,
  isStarting,
  onReset,
  activeJob,
  onPause,
  onResume,
  onRecheck,
  onStopSeeding,
  onCancel,
  onCancelJob,
  onRetry,
}) => {
  // Always prioritize metadata that has actual parsed files over incomplete shells
  const metadata = useMemo(() => {
    if (activeJob?.torrent_info?.has_metadata && (activeJob.torrent_info.files?.length ?? 0) > 0) {
      return activeJob.torrent_info;
    }
    if (propMetadata.has_metadata && (propMetadata.files?.length ?? 0) > 0) {
      return propMetadata;
    }
    if (activeJob?.torrent_info) {
      return activeJob.torrent_info;
    }
    return propMetadata;
  }, [propMetadata, activeJob?.torrent_info]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handlePause = useCallback(
    onPause ?? (async (jobId: string) => {
      try { await api.pauseTorrent(jobId); } catch (e) { console.error(e); }
    }),
    [onPause]
  );
  const handleResume = useCallback(
    onResume ?? (async (jobId: string) => {
      try { await api.resumeTorrent(jobId); } catch (e) { console.error(e); }
    }),
    [onResume]
  );
  const handleRecheck = useCallback(
    onRecheck ?? (async (jobId: string) => {
      try { await api.recheckTorrent(jobId); } catch (e) { console.error(e); }
    }),
    [onRecheck]
  );
  const handleStopSeeding = useCallback(
    onStopSeeding ?? (async (jobId: string) => {
      try { await api.stopSeeding(jobId); } catch (e) { console.error(e); }
    }),
    [onStopSeeding]
  );
  const handleCancel = onCancel ?? onCancelJob;

  // ── File selection state ───────────────────────────────────────────────────
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    () => new Set((metadata.files || []).map((f) => f.index))
  );
  const [filePriorities, setFilePriorities] = useState<Record<number, 'high' | 'normal' | 'low' | 'skip'>>(
    () => {
      const init: Record<number, 'high' | 'normal' | 'low' | 'skip'> = {};
      (metadata.files || []).forEach((f) => { init[f.index] = 'normal'; });
      return init;
    }
  );

  // ── Config state ───────────────────────────────────────────────────────────
  const [seedingMode, setSeedingMode] = useState<'stop' | 'ratio_1' | 'ratio_2' | 'time_30m' | 'time_2h' | 'indefinite'>('stop');
  const [destinationFolder, setDestinationFolder] = useState(metadata.name || '');

  // Sync state when metadata files or details arrive
  useEffect(() => {
    if (metadata.files && metadata.files.length > 0) {
      setSelectedIndices(new Set(metadata.files.map((f) => f.index)));
      const init: Record<number, 'high' | 'normal' | 'low' | 'skip'> = {};
      metadata.files.forEach((f) => { init[f.index] = 'normal'; });
      setFilePriorities(init);
    }
    if (metadata.name) {
      setDestinationFolder(metadata.name);
    }
  }, [metadata.info_hash, metadata.files?.length, metadata.name]);

  // ── UI state ───────────────────────────────────────────────────────────────
  const [copiedHash, setCopiedHash] = useState(false);
  const [searchFilter, setSearchFilter] = useState('');
  const [activeTab, setActiveTab] = useState<FileCategory>('all');
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());
  const [visibleLimit, setVisibleLimit] = useState(200);
  const [archiveDownloading, setArchiveDownloading] = useState(false);
  const [archiveError, setArchiveError] = useState<string | null>(null);

  // Storage Health state
  const [storageHealthy, setStorageHealthy] = useState<boolean>(true);
  const [storageErrorMsg, setStorageErrorMsg] = useState<string | null>(null);
  const [checkingStorage, setCheckingStorage] = useState(false);

  const verifyStorage = useCallback(async () => {
    try {
      setCheckingStorage(true);
      const res = await api.getStorageStatus();
      const dlTarget = res.targets.find((t) => t.target_type === 'downloads');
      if (dlTarget && !dlTarget.writable) {
        setStorageHealthy(false);
        setStorageErrorMsg(dlTarget.message || 'This location is not writable by container UID 10001:10001.');
      } else {
        setStorageHealthy(true);
        setStorageErrorMsg(null);
      }
    } catch (e) {
      console.error('Failed to verify storage in TorrentWorkspace', e);
    } finally {
      setCheckingStorage(false);
    }
  }, []);

  useEffect(() => {
    verifyStorage();
  }, [verifyStorage]);

  // ── Derived ────────────────────────────────────────────────────────────────
  const telemetry = activeJob?.torrent_telemetry;
  const isCompleted = activeJob?.status === 'COMPLETED';
  const isActive = !!activeJob && !isCompleted;
  const isLive = activeJob?.status === 'DOWNLOADING' || activeJob?.status === 'SEEDING' || activeJob?.status === 'PAUSED';

  // ── Selection helpers ──────────────────────────────────────────────────────
  const { selectedCount, selectedBytes } = useMemo(() => {
    let count = 0, bytes = 0;
    for (const f of (metadata.files || [])) {
      if (selectedIndices.has(f.index)) { count++; bytes += f.size; }
    }
    return { selectedCount: count, selectedBytes: bytes };
  }, [metadata.files, selectedIndices]);

  const handleSelectAll = useCallback(() =>
    setSelectedIndices(new Set((metadata.files || []).map((f) => f.index))), [metadata.files]);

  const handleDeselectAll = useCallback(() => setSelectedIndices(new Set()), []);

  const handleInvert = useCallback(() => {
    setSelectedIndices((prev) => {
      const next = new Set<number>();
      for (const f of (metadata.files || [])) {
        if (!prev.has(f.index)) next.add(f.index);
      }
      return next;
    });
  }, [metadata.files]);

  const handleSelectMediaOnly = useCallback(() => {
    const next = new Set<number>();
    for (const f of (metadata.files || [])) {
      const cat = getFileCategory(f.path);
      if (cat === 'video' || cat === 'audio') next.add(f.index);
    }
    setSelectedIndices(next);
  }, [metadata.files]);

  const toggleIndex = useCallback((idx: number, isSelected: boolean) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (isSelected) next.delete(idx); else next.add(idx);
      return next;
    });
  }, []);

  const gatherIndices = (node: TreeNode): number[] => {
    if (node.type === 'file') return [node.file.index];
    return node.children.flatMap(gatherIndices);
  };

  const toggleFolderSelection = useCallback((node: TreeNode, fullySelected: boolean) => {
    const indices = gatherIndices(node);
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      indices.forEach((idx) => { if (fullySelected) next.delete(idx); else next.add(idx); });
      return next;
    });
  }, []);

  const updatePriority = useCallback((idx: number, prio: 'high' | 'normal' | 'low' | 'skip') => {
    setFilePriorities((prev) => ({ ...prev, [idx]: prio }));
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (prio === 'skip') next.delete(idx); else next.add(idx);
      return next;
    });
  }, []);

  // ── Filtered file list ─────────────────────────────────────────────────────
  const filteredFiles = useMemo(() => {
    let files = metadata.files || [];
    if (activeTab !== 'all') {
      files = files.filter((f) => getFileCategory(f.path) === activeTab);
    }
    if (searchFilter.trim()) {
      const term = searchFilter.toLowerCase();
      files = files.filter((f) => f.path.toLowerCase().includes(term));
    }
    return files;
  }, [metadata.files, searchFilter, activeTab]);

  const tree = useMemo(() => buildTree(filteredFiles), [filteredFiles]);

  // ── Tab counts ─────────────────────────────────────────────────────────────
  const tabCounts = useMemo(() => {
    const fileList = metadata.files || [];
    const counts: Record<FileCategory, number> = { all: fileList.length, video: 0, audio: 0, documents: 0, archives: 0, other: 0 };
    for (const f of fileList) counts[getFileCategory(f.path)]++;
    return counts;
  }, [metadata.files]);

  // ── Start download ────────────────────────────────────────────────────────
  const handleStartDownload = useCallback(() => {
    const hasFiles = Boolean(metadata.has_metadata && metadata.files && metadata.files.length > 0);
    const config: TorrentDownloadConfig = {
      info_hash: metadata.info_hash,
      name: metadata.name,
      selected_indices: hasFiles ? Array.from(selectedIndices).sort((a, b) => a - b) : null,
      file_priorities: hasFiles ? filePriorities : null,
      destination_folder: destinationFolder.trim() || metadata.name,
      seeding_mode: seedingMode,
      magnet_uri: metadata.magnet_uri ?? undefined,
    };
    onStartDownload(config);
  }, [metadata, selectedIndices, filePriorities, destinationFolder, seedingMode, onStartDownload]);

  // ── Archive download ───────────────────────────────────────────────────────
  const handleArchiveDownload = async () => {
    if (!activeJob) return;
    setArchiveDownloading(true);
    setArchiveError(null);
    try {
      const url = activeJob.download_url || `/api/files/${activeJob.id}`;
      const filename = activeJob.output_filename
        ? (activeJob.output_filename.endsWith('.zip') ? activeJob.output_filename : `${activeJob.output_filename}.zip`)
        : `${activeJob.title || 'torrent'}.zip`;
      await api.downloadFile(url, filename);
    } catch (err: unknown) {
      setArchiveError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setArchiveDownloading(false);
    }
  };

  // ── Copy hash ─────────────────────────────────────────────────────────────
  const copyInfoHash = useCallback(() => {
    navigator.clipboard.writeText(metadata.info_hash);
    setCopiedHash(true);
    setTimeout(() => setCopiedHash(false), 2000);
  }, [metadata.info_hash]);

  // ── Tree rendering ────────────────────────────────────────────────────────
  const renderTreeNode = (node: TreeNode, depth: number): React.ReactNode => {
    if (node.type === 'folder') {
      const isExpanded = expandedFolders.has(node.path);
      const indices = gatherIndices(node);
      const selCount = indices.filter((i) => selectedIndices.has(i)).length;
      const fullySelected = indices.length > 0 && selCount === indices.length;
      const partial = selCount > 0 && selCount < indices.length;

      return (
        <div key={node.path}>
          <div
            className="flex items-center py-2 px-3 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
            style={{ paddingLeft: `${depth * 16 + 12}px` }}
          >
            <button
              className="p-1 mr-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 transition shrink-0"
              onClick={() => {
                setExpandedFolders((prev) => {
                  const next = new Set(prev);
                  if (isExpanded) next.delete(node.path); else next.add(node.path);
                  return next;
                });
              }}
              aria-label={isExpanded ? 'Collapse folder' : 'Expand folder'}
            >
              {isExpanded ? <CaretDown size={14} /> : <CaretRight size={14} />}
            </button>
            <input
              type="checkbox"
              checked={fullySelected}
              ref={(el) => { if (el) el.indeterminate = partial; }}
              onChange={() => toggleFolderSelection(node, fullySelected)}
              className="w-4 h-4 mr-2 rounded text-purple-600 focus:ring-purple-500 border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 shrink-0"
              aria-label={`Select folder ${node.name}`}
            />
            <Folder size={16} weight="fill" className="text-purple-400 mr-2 shrink-0" />
            <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 truncate flex-1">
              {node.name}
            </span>
            <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400 ml-3 shrink-0">
              {formatSize(node.size)}
            </span>
          </div>
          {isExpanded && (
            <div>{node.children.map((child) => renderTreeNode(child, depth + 1))}</div>
          )}
        </div>
      );
    }

    // File node
    const file = node.file;
    const isSelected = selectedIndices.has(file.index);
    const prio = filePriorities[file.index] ?? 'normal';

    return (
      <div
        key={file.index}
        className={`flex items-center justify-between py-2 gap-3 transition-colors ${
          isSelected
            ? 'bg-purple-500/[0.03] dark:bg-purple-500/[0.05]'
            : 'opacity-55 bg-zinc-50/40 dark:bg-zinc-900/30'
        }`}
        style={{ paddingLeft: `${depth * 16 + 38}px`, paddingRight: '12px' }}
      >
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => toggleIndex(file.index, isSelected)}
            className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 shrink-0"
            aria-label={`Select ${node.name}`}
          />
          {getFileIcon(file.path)}
          <span className="text-xs text-zinc-800 dark:text-zinc-200 truncate" title={file.path}>
            {node.name}
          </span>
        </div>
        <div className="flex items-center gap-2.5 shrink-0">
          <span className="text-[11px] font-mono text-zinc-500 dark:text-zinc-400 hidden sm:inline">
            {file.size_formatted}
          </span>
          <select
            value={prio}
            onChange={(e) => updatePriority(file.index, e.target.value as 'high' | 'normal' | 'low' | 'skip')}
            className="text-xs bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg px-2 py-1 text-zinc-700 dark:text-zinc-300 focus:outline-none focus:ring-1 focus:ring-purple-500 font-semibold"
            aria-label={`Priority for ${node.name}`}
          >
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
            <option value="skip">Skip</option>
          </select>
        </div>
      </div>
    );
  };

  // ── Flatten tree for limiting visible nodes ───────────────────────────────
  const flatNodes = useMemo(() => {
    const result: Array<{ node: TreeNode; depth: number }> = [];
    const walk = (nodes: TreeNode[], depth: number) => {
      for (const node of nodes) {
        result.push({ node, depth });
        if (node.type === 'folder' && expandedFolders.has(node.path)) {
          walk(node.children, depth + 1);
        }
      }
    };
    walk(tree, 0);
    return result;
  }, [tree, expandedFolders]);

  const visibleNodes = flatNodes.slice(0, visibleLimit);
  const hasMore = flatNodes.length > visibleLimit;

  // ── State stepper ─────────────────────────────────────────────────────────
  const renderStateStepper = () => {
    if (!activeJob) return null;
    const stat = activeJob.status;
    const steps = [
      {
        label: 'Metadata',
        isActive: stat === 'WAITING_FOR_METADATA' || stat === 'ACQUIRING_METADATA',
        isDone: metadata.has_metadata && stat !== 'WAITING_FOR_METADATA' && stat !== 'ACQUIRING_METADATA',
      },
      {
        label: 'Preparing',
        isActive: stat === 'QUEUED' || stat === 'ANALYZING' || stat === 'READY' || stat === 'WAITING_FOR_SELECTION',
        isDone: ['DOWNLOADING', 'PROCESSING', 'SEEDING', 'COMPLETED'].includes(stat),
      },
      {
        label: 'Downloading',
        isActive: stat === 'DOWNLOADING' || stat === 'PAUSED' || stat === 'INTERRUPTED',
        isDone: ['PROCESSING', 'SEEDING', 'COMPLETED'].includes(stat) || (activeJob.progress === 100 && stat !== 'PAUSED'),
        suffix: stat === 'PAUSED' ? '(Paused)' : '',
      },
      {
        label: 'Verifying',
        isActive: stat === 'PROCESSING',
        isDone: ['SEEDING', 'COMPLETED'].includes(stat),
      },
      {
        label: 'Seeding',
        isActive: stat === 'SEEDING',
        isDone: stat === 'COMPLETED',
      },
      {
        label: 'Completed',
        isActive: stat === 'COMPLETED',
        isDone: stat === 'COMPLETED',
      },
    ];

    return (
      <div className="p-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm overflow-x-auto">
        <div className="flex items-center min-w-max gap-1 text-[11px] font-bold">
          {steps.map((step, i) => (
            <React.Fragment key={step.label}>
              <div
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border whitespace-nowrap transition-colors ${
                  step.isActive && stat === 'PAUSED'
                    ? 'bg-zinc-800/70 text-zinc-400 border-zinc-700'
                    : step.isActive
                    ? 'bg-purple-900/40 text-purple-300 border-purple-700/50'
                    : step.isDone && !step.isActive
                    ? 'bg-purple-950/50 text-purple-300 border-purple-800/40'
                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-600 border-transparent'
                }`}
              >
                {step.isDone && !step.isActive && <Check size={12} weight="bold" />}
                <span>{step.label}{step.suffix ? ` ${step.suffix}` : ''}</span>
              </div>
              {i < steps.length - 1 && (
                <div className="w-4 h-[2px] bg-zinc-200 dark:bg-zinc-700 mx-1 shrink-0" />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  };

  // ── Completion panel ──────────────────────────────────────────────────────
  const renderCompletion = () => {
    if (!isCompleted || !activeJob) return null;
    const isDirectory = activeJob.output_type === 'directory';

    return (
      <div className="bg-purple-950/30 border border-purple-800/50 rounded-2xl p-6 space-y-5 shadow-lg">
        <div className="flex items-start gap-4">
          <div className="p-2.5 rounded-xl bg-purple-600 text-white shrink-0 shadow-purple-sm">
            <CheckCircle size={28} weight="fill" />
          </div>
          <div className="flex-1 min-w-0 space-y-1">
            <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-50">
              Torrent Download Complete
            </h3>
            <p className="text-xs font-mono text-zinc-600 dark:text-zinc-400 truncate" title={activeJob.title ?? undefined}>
              {activeJob.title || activeJob.output_filename}
            </p>
            <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-500 dark:text-zinc-400 pt-1">
              <span className="font-semibold text-purple-700 dark:text-purple-300 font-mono">
                {activeJob.file_count ?? 1} {(activeJob.file_count ?? 1) === 1 ? 'file' : 'files'}
              </span>
              {telemetry?.ratio !== undefined && (
                <span className="font-semibold text-purple-700 dark:text-purple-300 font-mono">
                  Ratio: {telemetry.ratio.toFixed(2)}×
                </span>
              )}
              {activeJob.info_hash && (
                <span className="font-mono text-zinc-500 hidden sm:inline">
                  {activeJob.info_hash.substring(0, 12)}…
                </span>
              )}
            </div>
          </div>
        </div>

        {archiveError && (
          <div className="p-3 bg-zinc-900/60 border border-zinc-700 rounded-xl text-xs text-zinc-400 flex items-center gap-2">
            <WarningCircle size={15} className="shrink-0" />
            <span>{archiveError}</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            type="button"
            onClick={handleArchiveDownload}
            disabled={archiveDownloading}
            className="flex-1 flex items-center justify-center gap-2 py-3 px-5 rounded-xl text-sm font-bold text-white bg-purple-600 hover:bg-purple-700 active:scale-[0.99] disabled:opacity-50 transition shadow-md shadow-purple-600/25"
          >
            {archiveDownloading ? (
              <><CircleNotch size={17} className="animate-spin" /><span>Preparing…</span></>
            ) : isDirectory ? (
              <><Archive size={17} weight="bold" /><span>Download Archive (.zip)</span></>
            ) : (
              <><DownloadSimple size={17} weight="bold" /><span>Save to Device</span></>
            )}
          </button>
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 border border-zinc-200 dark:border-zinc-700 transition"
            >
              <ArrowClockwise size={16} />
              <span>New Download</span>
            </button>
          )}
        </div>
      </div>
    );
  };

  // ─────────────────────────────────────────────────────────────────────────
  // RENDER
  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="w-full space-y-5">

      {/* ── 1. Hero Card ── */}
      <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-4">
        {/* Title row */}
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-1.5 min-w-0 flex-1">
            {/* Badges row */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800/80">
                <Magnet size={13} weight="bold" />
                {metadata.magnet_uri ? 'MAGNET' : 'TORRENT FILE'}
              </span>
              <StatePill status={activeJob?.status} hasMeta={metadata.has_metadata} />
            </div>

            {/* Torrent Name */}
            <h2
              className="text-lg sm:text-xl font-bold text-zinc-900 dark:text-zinc-100 leading-tight truncate"
              title={metadata.name}
            >
              {metadata.name}
            </h2>

            {/* Meta pills */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs font-mono text-zinc-500 dark:text-zinc-400">
              {metadata.has_metadata && (metadata.file_count ?? 0) > 0 ? (
                <span>{metadata.file_count} {metadata.file_count === 1 ? 'file' : 'files'}</span>
              ) : (
                <span>Metadata pending</span>
              )}
              {metadata.piece_count > 0 && (
                <span>· {metadata.piece_count} pieces ({formatSize(metadata.piece_length)} ea.)</span>
              )}
              {metadata.trackers?.length > 0 && (
                <span className="flex items-center gap-1">
                  <Users size={13} className="text-purple-400" />
                  {metadata.trackers.length} trackers
                </span>
              )}
            </div>
          </div>

          {/* Size + Reset */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              <p className="text-[10px] text-zinc-500 dark:text-zinc-400 uppercase tracking-wider font-semibold">Total Swarm Size</p>
              <p className="text-2xl font-black text-purple-600 dark:text-purple-400 tabular-nums">
                {metadata.has_metadata && metadata.total_size_formatted ? metadata.total_size_formatted : '—'}
              </p>
            </div>
            {onReset && (
              <button
                type="button"
                onClick={onReset}
                className="p-2 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl transition"
                title="Clear torrent"
                aria-label="Clear torrent"
              >
                <XCircle size={20} />
              </button>
            )}
          </div>
        </div>

        {/* Info Hash row */}
        <div className="pt-3 border-t border-zinc-100 dark:border-zinc-800 flex flex-col sm:flex-row sm:items-center gap-3 text-xs">
          <div className="flex items-center gap-2 font-mono text-zinc-600 dark:text-zinc-400 min-w-0">
            <span className="shrink-0 text-zinc-500 font-semibold">Hash:</span>
            <span
              className="truncate bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded select-all max-w-[200px] sm:max-w-[300px]"
              title={metadata.info_hash}
            >
              {metadata.info_hash}
            </span>
            <button
              type="button"
              onClick={copyInfoHash}
              className="p-1 text-zinc-400 hover:text-purple-600 dark:hover:text-purple-400 transition rounded"
              title="Copy info hash"
              aria-label="Copy info hash"
            >
              {copiedHash ? <Check size={14} weight="bold" /> : <Copy size={14} />}
            </button>
          </div>
        </div>

        {/* Error message */}
        {activeJob?.error_message && (
          <div className="p-3.5 bg-zinc-100 dark:bg-zinc-800/60 border border-zinc-300 dark:border-zinc-700 rounded-xl flex items-start justify-between gap-3 text-xs text-zinc-600 dark:text-zinc-400">
            <div className="flex items-start gap-2 min-w-0">
              <WarningCircle size={16} className="shrink-0 mt-0.5 text-zinc-500" />
              <div className="min-w-0">
                <p className="font-bold truncate">{activeJob.error_message}</p>
                {activeJob.error_message.toLowerCase().includes('metadata') && (
                  <p className="text-[11px] mt-0.5 opacity-80">
                    The torrent may be offline or its trackers may be unavailable.
                  </p>
                )}
              </div>
            </div>
            {onRetry && (
              <button
                type="button"
                onClick={() => onRetry!(activeJob.id)}
                className="px-3 py-1 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 font-semibold rounded-lg text-xs transition shrink-0"
              >
                Retry
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── 2. State Stepper (when job active) ── */}
      {isActive && renderStateStepper()}

      {/* ── 3. Metadata Acquisition Card ── */}
      {(!metadata.has_metadata || !metadata.files || metadata.files.length === 0) && !isCompleted && (
        <div className="p-5 bg-purple-950/20 border border-purple-800/40 rounded-2xl flex flex-col sm:flex-row sm:items-center gap-4">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <CircleNotch size={24} className="animate-spin text-purple-500 shrink-0" />
            <div className="min-w-0">
              <p className="text-sm font-bold text-purple-300">
                {telemetry?.metadata_phase === 'Metadata received'
                  ? (metadata.file_count && metadata.file_count > 0
                      ? `Metadata received · Preparing ${metadata.file_count.toLocaleString()} files...`
                      : 'Metadata received · Preparing file selection...')
                  : (telemetry?.metadata_phase || 'Acquiring torrent metadata...')}
              </p>
              <p className="text-xs text-purple-400/80 mt-0.5">
                {telemetry?.metadata_phase === 'Metadata received'
                  ? 'Building file manifest from swarm metadata...'
                  : 'Connecting to DHT nodes and peer swarm to retrieve file manifest and total size.'}
              </p>
              {telemetry?.metadata_phase !== 'Metadata received' && (
                <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs font-mono text-purple-400/80 mt-1">
                  {telemetry?.trackers_contacted !== undefined && (
                    <span>Trackers: {telemetry.trackers_contacted}</span>
                  )}
                  <span>DHT: {telemetry?.dht_active ? 'Active' : 'Waiting'}</span>
                  {(telemetry?.peers ?? 0) > 0 && <span>Peers: {telemetry?.peers}</span>}
                  {(telemetry?.metadata_retry_count ?? 0) > 0 && (
                    <span>Retry #{telemetry?.metadata_retry_count}</span>
                  )}
                </div>
              )}
            </div>
          </div>
          {!activeJob && (
            <button
              type="button"
              onClick={handleStartDownload}
              disabled={isStarting}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 shrink-0 self-end sm:self-auto shadow-sm"
            >
              <Lightning size={15} weight="fill" />
              Start in Background
            </button>
          )}
        </div>
      )}

      {/* ── 4. Completion Panel ── */}
      {isCompleted && renderCompletion()}

      {/* ── 5. Live Telemetry (Downloading / Seeding / Paused) ── */}
      {isLive && (
        <div className="p-5 sm:p-6 bg-purple-950/20 border border-purple-800/40 rounded-2xl space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-purple-800/30">
            <h3 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
              <Broadcast size={16} className="text-purple-400" />
              <span>Live Swarm Telemetry</span>
            </h3>
            {activeJob?.info_hash && (
              <span className="text-[11px] font-mono text-zinc-400">
                {activeJob.info_hash.substring(0, 8)}...{activeJob.info_hash.substring(32)}
              </span>
            )}
          </div>
          {/* Top row: progress + actions */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            {/* Progress */}
            <div className="flex items-center gap-4">
              <div className="relative w-14 h-14 shrink-0">
                <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                  <circle cx="18" cy="18" r="15.9" fill="none" className="stroke-purple-900/50" strokeWidth="3" />
                  <circle
                    cx="18" cy="18" r="15.9" fill="none"
                    className="stroke-purple-500 transition-all duration-500"
                    strokeWidth="3"
                    strokeDasharray={`${(activeJob!.progress / 100) * 100} 100`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-purple-400">
                  {Math.round(activeJob!.progress)}%
                </span>
              </div>
              <div>
                {activeJob!.status === 'PAUSED' ? (
                  <p className="text-base font-bold text-zinc-300">Download Paused</p>
                ) : (
                  <p className="text-base font-bold text-zinc-100">
                    {telemetry?.downloaded_bytes
                      ? formatSize(telemetry.downloaded_bytes)
                      : telemetry?.total_downloaded
                      ? formatSize(telemetry.total_downloaded)
                      : '0 B'}
                    <span className="text-zinc-500 font-normal text-sm">
                      {' '}/ {telemetry?.total_size_formatted || metadata.total_size_formatted}
                    </span>
                  </p>
                )}
                <p className="text-xs text-purple-400 font-semibold uppercase tracking-wide mt-0.5">
                  {activeJob!.status === 'PAUSED'
                    ? 'Progress is preserved on disk'
                    : activeJob!.status === 'SEEDING'
                    ? `Seeding · Ratio ${(telemetry?.ratio ?? 0).toFixed(2)}×`
                    : activeJob!.current_stage || 'Downloading'}
                </p>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              {activeJob!.status === 'PAUSED' ? (
                <button
                  type="button"
                  onClick={() => handleResume(activeJob!.id)}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-bold rounded-xl bg-purple-600 hover:bg-purple-700 text-white transition shadow-sm"
                >
                  <Play size={16} weight="fill" /><span>Resume</span>
                </button>
              ) : activeJob!.status === 'DOWNLOADING' ? (
                <button
                  type="button"
                  onClick={() => handlePause(activeJob!.id)}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition"
                >
                  <Pause size={15} weight="fill" /><span>Pause</span>
                </button>
              ) : null}

              {activeJob!.status === 'SEEDING' && (
                <button
                  type="button"
                  onClick={() => handleStopSeeding(activeJob!.id)}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-zinc-700 transition"
                >
                  <StopCircle size={15} /><span>Stop Seeding</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => handleRecheck(activeJob!.id)}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-500 dark:text-zinc-400 border border-zinc-800 transition"
                title="Force verify downloaded pieces"
              >
                <ArrowClockwise size={14} /><span>Recheck</span>
              </button>

              {handleCancel && (
                <button
                  type="button"
                  onClick={() => handleCancel!(activeJob!.id)}
                  className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-zinc-900/60 hover:bg-zinc-800 text-zinc-500 border border-zinc-800 transition"
                >
                  <XCircle size={14} /><span>Cancel</span>
                </button>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 transition-all duration-500 ease-out rounded-full"
              style={{ width: `${Math.min(100, Math.max(0, activeJob!.progress))}%` }}
            />
          </div>

          {/* Telemetry grid */}
          {telemetry && activeJob!.status !== 'PAUSED' && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
              {activeJob!.status !== 'SEEDING' && (
                <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/80">
                  <p className="text-zinc-500 font-medium text-[10px] uppercase tracking-wider">Download</p>
                  <p className="text-sm font-bold text-purple-400 font-mono flex items-center gap-1 mt-0.5">
                    <Speedometer size={15} />
                    {telemetry.download_rate_human || telemetry.download_speed || '0 B/s'}
                  </p>
                </div>
              )}

              <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/80">
                <p className="text-zinc-500 font-medium text-[10px] uppercase tracking-wider">Upload</p>
                <p className="text-sm font-bold text-zinc-300 font-mono flex items-center gap-1 mt-0.5">
                  <ArrowsDownUp size={15} />
                  {telemetry.upload_rate_human || telemetry.upload_speed || '0 B/s'}
                </p>
              </div>

              <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/80">
                <p className="text-zinc-500 font-medium text-[10px] uppercase tracking-wider">Peers / Seeds</p>
                <p className="text-sm font-bold text-zinc-300 font-mono flex items-center gap-1 mt-0.5">
                  <Users size={15} />
                  {telemetry.num_seeds !== undefined
                    ? `${telemetry.num_seeds} (${telemetry.total_seeds || telemetry.num_seeds}) seeds • ${telemetry.num_peers} (${telemetry.total_peers || telemetry.num_peers}) peers`
                    : `${telemetry.seeds ?? 0} seeds (${telemetry.peers ?? 0} peers)`}
                </p>
              </div>

              <div className="p-3 bg-zinc-950/60 rounded-xl border border-zinc-800/80">
                <p className="text-zinc-500 font-medium text-[10px] uppercase tracking-wider">
                  {activeJob!.status === 'SEEDING' ? 'Ratio / Uploaded' : 'Ratio / ETA'}
                </p>
                <div className="mt-0.5 space-y-0.5">
                  <p className="text-sm font-bold text-zinc-300 font-mono">{(telemetry.ratio ?? 0).toFixed(2)}×</p>
                  {activeJob!.status === 'SEEDING' ? (
                    <p className="text-[11px] text-purple-400 font-mono">
                      {telemetry.uploaded_bytes ? formatSize(telemetry.uploaded_bytes) : (telemetry.total_uploaded ? formatSize(telemetry.total_uploaded) : '0 B')} up
                    </p>
                  ) : (
                    <p className="text-[11px] text-purple-400 font-mono">
                      ETA {telemetry.eta_human || telemetry.eta || '∞'}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Seeding rule note */}
          {activeJob!.status === 'SEEDING' && telemetry?.seeding_mode && (
            <div className="flex items-center gap-2 text-xs text-purple-400/70 font-mono">
              <Broadcast size={13} />
              <span>Seeding rule: {telemetry.seeding_mode}</span>
            </div>
          )}
        </div>
      )}

      {/* ── 6. File Browser (only when metadata available + files exist) ── */}
      {metadata.has_metadata && metadata.files?.length > 0 && !isCompleted && (
        <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-4">
          {/* Header */}
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <HardDrives size={18} className="text-purple-500" />
                File Selection
              </h3>
              <div className="mt-1 inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-xs font-mono text-zinc-600 dark:text-zinc-400">
                <span className="font-bold text-purple-600 dark:text-purple-400">{selectedCount}</span>
                <span>of {metadata.files.length} files selected</span>
                <span>·</span>
                <span className="font-bold text-purple-600 dark:text-purple-400">{formatSize(selectedBytes)}</span>
              </div>
            </div>

            {/* Search + toolbar */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Search files…"
                className="text-xs px-3 py-1.5 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-purple-500 text-zinc-900 dark:text-zinc-100 placeholder:text-zinc-400 sm:w-48"
              />
              <div className="flex items-center gap-1 overflow-x-auto pb-0.5">
                {[
                  { label: 'All', action: handleSelectAll, icon: <CheckSquare size={13} /> },
                  { label: 'None', action: handleDeselectAll, icon: <Square size={13} /> },
                  { label: 'Invert', action: handleInvert, icon: <ArrowsLeftRight size={13} /> },
                ].map(({ label, action, icon }) => (
                  <button
                    key={label}
                    type="button"
                    onClick={action}
                    className="flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700 whitespace-nowrap transition"
                  >
                    {icon}<span>{label}</span>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={handleSelectMediaOnly}
                  className="flex items-center gap-1 px-2.5 py-1 text-xs font-bold rounded-lg bg-purple-50 dark:bg-purple-900/40 text-purple-700 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-800/60 whitespace-nowrap transition"
                >
                  <Video size={13} /><span>Media Only</span>
                </button>
              </div>
            </div>
          </div>

          {/* Filter tabs */}
          <div className="flex items-center gap-1.5 border-b border-zinc-200 dark:border-zinc-800 pb-2 overflow-x-auto">
            {(
              [
                { id: 'all', label: 'All' },
                { id: 'video', label: 'Video' },
                { id: 'audio', label: 'Audio' },
                { id: 'documents', label: 'Docs' },
                { id: 'archives', label: 'Archives' },
                { id: 'other', label: 'Other' },
              ] as { id: FileCategory; label: string }[]
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300'
                    : 'text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800'
                }`}
              >
                <span>{tab.label}</span>
                {tabCounts[tab.id] > 0 && (
                  <span className="text-[10px] font-mono opacity-70">({tabCounts[tab.id]})</span>
                )}
              </button>
            ))}
          </div>

          {/* Tree */}
          <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-hidden bg-zinc-50/40 dark:bg-zinc-950/30">
            <div className="max-h-96 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-800/60">
              {visibleNodes.length === 0 ? (
                <div className="p-8 text-center text-zinc-500 dark:text-zinc-400 text-sm">
                  No files match the current filter.
                </div>
              ) : (
                visibleNodes.map(({ node, depth }) => renderTreeNode(node, depth))
              )}
            </div>
            {hasMore && (
              <div className="p-3 text-center bg-zinc-100/80 dark:bg-zinc-900/80 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setVisibleLimit((prev) => prev + 200)}
                  className="text-xs font-semibold text-purple-600 dark:text-purple-400 hover:underline"
                >
                  Load more ({flatNodes.length - visibleLimit} remaining)…
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Metadata pending placeholder (no metadata yet, no files) */}
      {!metadata.has_metadata && (!metadata.files || metadata.files.length === 0) && !activeJob && (
        <div className="p-8 text-center space-y-4 bg-zinc-50 dark:bg-zinc-800/40 rounded-2xl border border-zinc-200 dark:border-zinc-800">
          <div className="w-12 h-12 rounded-2xl bg-purple-500/10 text-purple-500 flex items-center justify-center mx-auto">
            <CircleNotch size={28} className="animate-spin" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-zinc-800 dark:text-zinc-200">
              Metadata is being retrieved in the background...
            </h4>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 max-w-sm mx-auto">
              Safe default policy: all files will be automatically downloaded.
            </p>
          </div>
          <div className="pt-2 flex items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleStartDownload}
              disabled={isStarting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs text-white bg-purple-600 hover:bg-purple-700 active:scale-95 shadow-md shadow-purple-600/20 transition disabled:opacity-50"
            >
              <Lightning size={15} weight="fill" />
              <span>Start in Background</span>
            </button>
          </div>
        </div>
      )}

      {/* ── 7. Config + Action ── */}
      {!isCompleted && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Seeding Policy */}
          <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm space-y-4">
            <div>
              <h4 className="text-sm font-bold text-zinc-900 dark:text-zinc-100">Seeding Policy</h4>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
                When to stop uploading after download completes.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'stop', label: 'Stop immediately' },
                { id: 'ratio_1', label: 'Ratio 1.0' },
                { id: 'ratio_2', label: 'Ratio 2.0' },
                { id: 'time_30m', label: '30 Minutes' },
                { id: 'time_2h', label: '2 Hours' },
                { id: 'indefinite', label: 'Indefinitely' },
              ].map((opt) => (
                <label
                  key={opt.id}
                  className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors ${
                    seedingMode === opt.id
                      ? 'border-purple-500 bg-purple-50 dark:bg-purple-950/40'
                      : 'border-zinc-200 dark:border-zinc-800 hover:border-purple-300 dark:hover:border-purple-800'
                  }`}
                >
                  <input
                    type="radio"
                    name="seedingMode"
                    value={opt.id}
                    checked={seedingMode === opt.id}
                    onChange={() => setSeedingMode(opt.id as typeof seedingMode)}
                    className="text-purple-600 focus:ring-purple-500 border-zinc-300 dark:border-zinc-700"
                  />
                  <span className="text-xs font-semibold text-zinc-800 dark:text-zinc-200">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Destination + Start */}
          <div className="p-5 sm:p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm flex flex-col justify-between gap-5">
            <div className="space-y-2">
              <label className="flex items-center gap-1.5 text-sm font-bold text-zinc-900 dark:text-zinc-100">
                <FolderOpen size={16} className="text-purple-500" />
                Destination Folder
              </label>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                Saved under <code className="font-mono text-purple-600 dark:text-purple-400">/data/downloads/</code> and indexed into Library automatically.
              </p>
              <input
                type="text"
                value={destinationFolder}
                onChange={(e) => setDestinationFolder(e.target.value)}
                placeholder="Folder name"
                className="w-full text-xs font-mono px-3.5 py-2.5 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-purple-500 text-zinc-900 dark:text-zinc-100"
              />
            </div>

            {/* Storage Health Warning Banner */}
            {!storageHealthy && (
              <div className="p-3.5 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 rounded-xl space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold text-red-700 dark:text-red-300">
                    <WarningCircle size={16} weight="fill" />
                    <span>Destination Unavailable</span>
                  </div>
                  <button
                    type="button"
                    onClick={verifyStorage}
                    disabled={checkingStorage}
                    className="inline-flex items-center gap-1 font-bold text-purple-600 dark:text-purple-400 hover:underline"
                  >
                    <ArrowClockwise size={12} className={checkingStorage ? 'animate-spin' : ''} />
                    <span>{checkingStorage ? 'Checking…' : 'Recheck Storage'}</span>
                  </button>
                </div>
                <div className="font-mono text-[11px] text-zinc-500">/data/downloads</div>
                <p className="text-[11px] text-red-700 dark:text-red-300 leading-relaxed">
                  {storageErrorMsg || 'The container user (UID 10001:10001) cannot create files in this directory. Fix NAS permissions or use a Docker-managed volume.'}
                </p>
              </div>
            )}

            {(!activeJob || activeJob.status === 'WAITING_FOR_SELECTION' || activeJob.status === 'READY') && (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={handleStartDownload}
                  disabled={
                    isStarting ||
                    !storageHealthy ||
                    (metadata.has_metadata && metadata.files?.length > 0 && selectedCount === 0)
                  }
                  className="w-full flex items-center justify-center gap-2 py-3.5 px-5 rounded-xl font-bold text-sm text-white bg-purple-600 hover:bg-purple-700 active:scale-[0.99] disabled:opacity-40 disabled:cursor-not-allowed transition shadow-md shadow-purple-500/20"
                >
                  {isStarting ? (
                    <><CircleNotch size={18} className="animate-spin" /><span>Starting…</span></>
                  ) : !storageHealthy ? (
                    <>
                      <WarningCircle size={18} weight="bold" />
                      <span>Destination Unavailable — Storage Not Writable</span>
                    </>
                  ) : (
                    <>
                      <Lightning size={18} weight="fill" />
                      <span>
                        {metadata.has_metadata && metadata.files?.length > 0
                          ? `Start BitTorrent Download (${formatSize(selectedBytes)})`
                          : 'Start in Background'}
                      </span>
                    </>
                  )}
                </button>
                <p className="text-[11px] text-center text-zinc-400 dark:text-zinc-500">
                  Active torrent downloads are protected from retention cleanup.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
