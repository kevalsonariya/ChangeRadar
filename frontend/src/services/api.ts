import axios, { type AxiosError } from 'axios';
import type { 
  MonitoredWebsite, 
  ChangeRecord, 
  DeadlineItem, 
  NotificationItem, 
  DashboardSummary 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

export interface ApiResult<T> {
  success: boolean;
  data: T | null;
  error?: string;
  isBackendOffline?: boolean;
}

/**
 * Helper to handle API errors cleanly without throwing unhandled exceptions.
 */
function handleApiError<T>(error: unknown): ApiResult<T> {
  if (axios.isAxiosError(error)) {
    const axiosErr = error as AxiosError;
    if (!axiosErr.response || axiosErr.code === 'ERR_NETWORK' || axiosErr.code === 'ECONNREFUSED') {
      return {
        success: false,
        data: null,
        error: `FastAPI backend is unreachable at ${API_BASE_URL}. Ensure uvicorn is running.`,
        isBackendOffline: true,
      };
    }
    return {
      success: false,
      data: null,
      error: `API error (${axiosErr.response.status}): ${axiosErr.message}`,
    };
  }
  return {
    success: false,
    data: null,
    error: error instanceof Error ? error.message : 'Unknown network error',
  };
}

// -------------------------------------------------------------
// Real Backend API Methods (Do NOT mock inside these functions)
// -------------------------------------------------------------

export async function checkBackendHealth(): Promise<ApiResult<{ status: string; database: string }>> {
  try {
    const res = await apiClient.get('/health');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchWebsitesApi(): Promise<ApiResult<MonitoredWebsite[]>> {
  try {
    const res = await apiClient.get<MonitoredWebsite[]>('/api/websites');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function createWebsiteApi(website: {
  name: string;
  url: string;
  category?: string;
  selector?: string;
  check_interval_minutes?: number;
}): Promise<ApiResult<MonitoredWebsite>> {
  try {
    const res = await apiClient.post<MonitoredWebsite>('/api/websites', website);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function deleteWebsiteApi(websiteId: number): Promise<ApiResult<{ status: string; id: number }>> {
  try {
    const res = await apiClient.delete(`/api/websites/${websiteId}`);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchChangesApi(): Promise<ApiResult<ChangeRecord[]>> {
  try {
    const res = await apiClient.get<ChangeRecord[]>('/api/changes');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchDeadlinesApi(): Promise<ApiResult<DeadlineItem[]>> {
  try {
    const res = await apiClient.get<DeadlineItem[]>('/api/deadlines');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchSummaryApi(): Promise<ApiResult<DashboardSummary>> {
  try {
    const res = await apiClient.get<DashboardSummary>('/api/deadlines/summary');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchNotificationsApi(): Promise<ApiResult<NotificationItem[]>> {
  try {
    const res = await apiClient.get<NotificationItem[]>('/api/notifications');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}
