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
  filesize_approx: string | null;
  ext: string;
}

export interface AudioQualityOption {
  label: string;
  format: string;
  ext: string;
}

export interface AnalyzeResponse {
  url: string;
  title: string;
  thumbnail: string | null;
  duration: number | null;
  duration_string: string | null;
  uploader: string | null;
  webpage_url: string;
  extractor: string;
  video_available: boolean;
  audio_available: boolean;
  video_options: VideoQualityOption[];
  audio_options: AudioQualityOption[];
  supported_containers: string[];
}

export interface DownloadRequest {
  url: string;
  title?: string;
  resolution?: string;
  audio_only?: boolean;
  audio_format?: string;
  output_container?: string;
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
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  active_count: number;
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
}
