import { useEffect, useState } from 'react';
import { JobResponse } from '../types';
import { api } from '../services/api';

export function useJobEvents(jobId: string | null) {
  const [job, setJob] = useState<JobResponse | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      setIsConnected(false);
      return;
    }

    let eventSource: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;
    let isTerminated = false;

    // Start SSE stream
    try {
      eventSource = new EventSource(`/api/jobs/${jobId}/events`);

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
      };

      eventSource.onmessage = (event) => {
        try {
          const data: JobResponse = JSON.parse(event.data);
          setJob(data);

          if (data.status === 'COMPLETED' || data.status === 'FAILED' || data.status === 'CANCELLED') {
            isTerminated = true;
            eventSource?.close();
            setIsConnected(false);
          }
        } catch (e) {
          console.error('Error parsing SSE event data:', e);
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        // Fallback: poll every 2 seconds if SSE is interrupted
        if (!isTerminated && !pollInterval) {
          pollInterval = setInterval(async () => {
            try {
              const latest = await api.getJob(jobId);
              setJob(latest);
              if (
                latest.status === 'COMPLETED' ||
                latest.status === 'FAILED' ||
                latest.status === 'CANCELLED'
              ) {
                if (pollInterval) clearInterval(pollInterval);
                pollInterval = null;
              }
            } catch (err) {
              console.error('Error polling job:', err);
            }
          }, 2000);
        }
      };
    } catch (e) {
      console.error('EventSource initialization failed, using polling fallback:', e);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [jobId]);

  return { job, isConnected, error };
}
