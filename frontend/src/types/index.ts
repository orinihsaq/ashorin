export type JobStatus =
  | 'QUEUED'
  | 'ANALYZING'
  | 'DOWNLOADING'
  | 'PROCESSING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface VideoQualityOption {
  label: string;
  resolution: string;
  height: number | null;
  width?: number | null;
  fps?: number | null;
  vcodec?: string | null;
  acodec?: string | null;
  filesize_approx: string | null;
  tbr?: number | null;
  ext: string;
}

export interface AudioQualityOption {
  label: string;
  format: string;
  ext: string;
  bitrate?: string | null;
}

export interface TechnicalSummary {
  resolution_str?: string | null;
  fps?: number | null;
  vcodec?: string | null;
  acodec?: string | null;
  tbr?: number | null;
  format_count: number;
  media_type: string;
}

export interface AnalyzeResponse {
  url: string;
  title: string;
  thumbnail: string | null;
  duration: number | null;
  duration_string: string | null;
  uploader: string | null;
  uploader_avatar?: string | null;
  upload_date?: string | null;
  view_count?: number | null;
  like_count?: number | null;
  webpage_url: string;
  extractor: string;
  media_type: string;
  video_available: boolean;
  audio_available: boolean;
  video_options: VideoQualityOption[];
  audio_options: AudioQualityOption[];
  supported_containers: string[];
  technical_summary?: TechnicalSummary | null;
}

export interface DownloadConfig {
  preset: string;
  quality: string;
  output_container: string;
  audio_mode: 'merge' | 'audio_only';
  audio_format: string;
  audio_quality: string;
  video_codec: string;
  filename_template: string;
  subtitles: boolean;
  embed_subtitles: boolean;
  auto_subtitles: boolean;
  subtitle_langs: string;
  embed_metadata: boolean;
  embed_thumbnail: boolean;
  write_chapters: boolean;
  retries: number;
  timeout: number;
  concurrent_fragments: number;
  playlist_mode: 'single' | 'playlist';
  playlist_items?: string | null;
}

export interface PresetDefinition {
  id: string;
  name: string;
  description: string;
  badge?: string | null;
  config: DownloadConfig;
}

export interface PresetsResponse {
  presets: PresetDefinition[];
  default_preset: string;
}

export interface DownloadRequest {
  url: string;
  title?: string;
  resolution?: string;
  audio_only?: boolean;
  audio_format?: string;
  output_container?: string;
  config?: DownloadConfig;
}

export interface DownloadResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface JobResponse {
  id: string;
  url: string;
  title: string | null;
  thumbnail: string | null;
  status: JobStatus;
  progress: number;
  speed: string | null;
  eta: string | null;
  current_stage: string;
  downloaded_bytes: number;
  total_bytes: number | null;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
  output_filename: string | null;
  output_filesize: number | null;
  output_filesize_formatted: string | null;
  error_message: string | null;
  download_url: string | null;
  config_summary?: string | null;
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  active_count: number;
}

export interface StorageInfo {
  total_bytes: number;
  free_bytes: number;
  used_bytes: number;
  percent_used: number;
  free_formatted: string;
  total_formatted: string;
  used_formatted: string;
}

export interface SystemInfoResponse {
  app_name: string;
  app_version: string;
  ytdlp_version: string;
  latest_ytdlp_version: string | null;
  update_available: boolean;
  ffmpeg_available: boolean;
  ffmpeg_version: string | null;
  active_jobs: number;
  max_concurrent_downloads: number;
  download_retention: number;
  temp_retention: number;
  max_download_size: string;
  storage_info?: StorageInfo | null;
}
