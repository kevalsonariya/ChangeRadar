export type NavigationTab = 
  | 'dashboard' 
  | 'watchlist' 
  | 'history' 
  | 'deadlines' 
  | 'notifications' 
  | 'settings';

export type WebsiteStatus = 'active' | 'warning' | 'error' | 'paused';

export interface MonitoredWebsite {
  id: number;
  name: string;
  url: string;
  category: string;
  selector?: string;
  check_interval_minutes: number;
  status: WebsiteStatus;
  last_checked_at?: string;
  last_change_at?: string;
  change_count: number;
  created_at: string;
}

export type ChangeType = 'addition' | 'deletion' | 'modification';

export interface ChangeRecord {
  id: number;
  website_id: number;
  website_name: string;
  detected_at: string;
  summary: string;
  change_type: ChangeType;
  additions_count: number;
  deletions_count: number;
  old_content_snippet?: string;
  new_content_snippet?: string;
  diff_unified?: string;
  is_read: boolean;
}

export type DeadlinePriority = 'high' | 'medium' | 'low';
export type DeadlineStatus = 'upcoming' | 'critical' | 'passed';

export interface DeadlineItem {
  id: number;
  website_id?: number;
  title: string;
  due_date: string;
  days_left: number;
  source_url: string;
  priority: DeadlinePriority;
  status: DeadlineStatus;
  category: string;
  description?: string;
}

export interface NotificationItem {
  id: number;
  type: 'change' | 'deadline' | 'system';
  title: string;
  message: string;
  timestamp: string;
  is_read: boolean;
  target_url?: string;
}

export interface DashboardSummary {
  active_monitors_count: number;
  total_changes_detected: number;
  upcoming_deadlines_count: number;
  unread_notifications_count: number;
  health_status: string;
}

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}
