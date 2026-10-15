import axios, { type AxiosError } from 'axios';
import type { 
  MonitoredWebsite, 
  ChangeRecord, 
  CheckWebsiteResult,
  DeadlineItem, 
  NotificationItem, 
  DashboardSummary 
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  withCredentials: true,
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
    const axiosErr = error as AxiosError<{ detail?: string }>;
    if (!axiosErr.response || axiosErr.code === 'ERR_NETWORK' || axiosErr.code === 'ECONNREFUSED') {
      return {
        success: false,
        data: null,
        error: `FastAPI backend is unreachable at ${API_BASE_URL}. Ensure uvicorn is running.`,
        isBackendOffline: true,
      };
    }
    const backendDetail = axiosErr.response.data?.detail || axiosErr.message;
    return {
      success: false,
      data: null,
      error: `API error (${axiosErr.response.status}): ${backendDetail}`,
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

export async function checkWebsiteApi(websiteId: number): Promise<ApiResult<CheckWebsiteResult>> {
  try {
    const res = await apiClient.post<CheckWebsiteResult>(`/api/websites/${websiteId}/check`);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchChangesApi(websiteId?: number): Promise<ApiResult<ChangeRecord[]>> {
  try {
    const url = websiteId ? `/api/changes?website_id=${websiteId}` : '/api/changes';
    const res = await apiClient.get<ChangeRecord[]>(url);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function fetchChangeDetailsApi(changeId: number): Promise<ApiResult<ChangeRecord>> {
  try {
    const res = await apiClient.get<ChangeRecord>(`/api/changes/${changeId}`);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function markChangeReadApi(changeId: number): Promise<ApiResult<ChangeRecord>> {
  try {
    const res = await apiClient.patch<ChangeRecord>(`/api/changes/${changeId}/read`);
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

export async function createDeadlineApi(deadline: {
  title: string;
  due_date: string;
  priority?: string;
  category?: string;
  description?: string;
  website_id?: number;
  source_url?: string;
}): Promise<ApiResult<DeadlineItem>> {
  try {
    const res = await apiClient.post<DeadlineItem>('/api/deadlines', deadline);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function updateDeadlineApi(
  deadlineId: number,
  payload: Partial<DeadlineItem>
): Promise<ApiResult<DeadlineItem>> {
  try {
    const res = await apiClient.put<DeadlineItem>(`/api/deadlines/${deadlineId}`, payload);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function toggleDeadlineCompleteApi(
  deadlineId: number,
  is_completed?: boolean
): Promise<ApiResult<DeadlineItem>> {
  try {
    const res = await apiClient.patch<DeadlineItem>(
      `/api/deadlines/${deadlineId}/complete`,
      is_completed !== undefined ? { is_completed } : {}
    );
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function deleteDeadlineApi(deadlineId: number): Promise<ApiResult<{ message: string; id: number }>> {
  try {
    const res = await apiClient.delete(`/api/deadlines/${deadlineId}`);
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

export async function markNotificationReadApi(notificationId: number): Promise<ApiResult<NotificationItem>> {
  try {
    const res = await apiClient.patch<NotificationItem>(`/api/notifications/${notificationId}/read`);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function markAllNotificationsReadApi(): Promise<ApiResult<{ message: string; updated_count: number }>> {
  try {
    const res = await apiClient.post<{ message: string; updated_count: number }>('/api/notifications/read-all');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

// -------------------------------------------------------------
// Authentication & User Account API Methods
// -------------------------------------------------------------

export async function registerApi(payload: {
  name: string;
  email: string;
  password: string;
  confirm_password: string;
}): Promise<ApiResult<any>> {
  try {
    const res = await apiClient.post('/api/auth/register', payload);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function loginApi(payload: {
  email: string;
  password: string;
}): Promise<ApiResult<any>> {
  try {
    const res = await apiClient.post('/api/auth/login', payload);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function logoutApi(): Promise<ApiResult<{ message: string }>> {
  try {
    const res = await apiClient.post('/api/auth/logout');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function getMeApi(): Promise<ApiResult<any>> {
  try {
    const res = await apiClient.get('/api/auth/me');
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function updateSettingsApi(settings: {
  email_notifications_enabled?: boolean;
  name?: string;
}): Promise<ApiResult<any>> {
  try {
    const res = await apiClient.patch('/api/auth/settings', settings);
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function verifyEmailApi(token: string): Promise<ApiResult<{ success: boolean; message: string; email_verified: boolean }>> {
  try {
    const res = await apiClient.post('/api/auth/verify-email', { token });
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

export async function resendVerificationApi(email?: string): Promise<ApiResult<{ success: boolean; message: string; token?: string }>> {
  try {
    const res = await apiClient.post('/api/auth/resend-verification', { email });
    return { success: true, data: res.data };
  } catch (err) {
    return handleApiError(err);
  }
}

