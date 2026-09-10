import {
  AnalyzeResponse,
  DownloadRequest,
  DownloadResponse,
  JobListResponse,
  JobResponse,
  PresetsResponse,
  SystemInfoResponse,
} from '../types';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Request failed with status ${res.status}`;
    try {
      const data = await res.json();
      if (data && data.detail) {
        errMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // Body not JSON
    }
    throw new ApiError(errMsg, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  async getPresets(): Promise<PresetsResponse> {
    const res = await fetch('/api/presets');
    return handleResponse<PresetsResponse>(res);
  },

  async analyzeUrl(url: string): Promise<AnalyzeResponse> {
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    return handleResponse<AnalyzeResponse>(res);
  },

  async startDownload(req: DownloadRequest): Promise<DownloadResponse> {
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<DownloadResponse>(res);
  },

  async getJobs(): Promise<JobListResponse> {
    const res = await fetch('/api/jobs');
    return handleResponse<JobListResponse>(res);
  },

  async getJob(jobId: string): Promise<JobResponse> {
    const res = await fetch(`/api/jobs/${jobId}`);
    return handleResponse<JobResponse>(res);
  },

  async cancelJob(jobId: string): Promise<{ job_id: string; status: string; message: string }> {
    const res = await fetch(`/api/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async deleteJob(jobId: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`/api/jobs/${jobId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async getSystemInfo(): Promise<SystemInfoResponse> {
    const res = await fetch('/api/system');
    return handleResponse<SystemInfoResponse>(res);
  },

  async updateYtDlp(): Promise<{ success: boolean; message: string; current_version: string }> {
    const res = await fetch('/api/system/update-ytdlp', {
      method: 'POST',
    });
    return handleResponse(res);
  },
};
