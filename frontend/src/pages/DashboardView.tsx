import React from 'react';
import { 
  Globe, 
  History, 
  CalendarClock, 
  Bell, 
  ArrowUpRight, 
  ExternalLink, 
  Clock, 
  Plus, 
  Flame,
  ArrowRight
} from 'lucide-react';
import type { 
  MonitoredWebsite, 
  ChangeRecord, 
  DeadlineItem, 
  NotificationItem, 
  NavigationTab 
} from '../types';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { DiffViewer } from '../components/common/DiffViewer';

interface DashboardViewProps {
  websites: MonitoredWebsite[];
  changes: ChangeRecord[];
  deadlines: DeadlineItem[];
  notifications: NotificationItem[];
  onNavigate: (tab: NavigationTab) => void;
  onOpenAddModal: () => void;
  onRefreshAll: () => void;
  isRefreshing: boolean;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  websites,
  changes,
  deadlines,
  notifications,
  onNavigate,
  onOpenAddModal,
}) => {
  const activeWebsitesCount = websites.filter(w => w.status === 'active').length;
  const criticalDeadlines = deadlines.filter(d => d.status === 'critical' || d.days_left <= 3);
  const unreadChanges = changes.filter(c => !c.is_read);
  const unreadNotifications = notifications.filter(n => !n.is_read);

  // Top highlight change for preview
  const featuredChange = changes[0];

  return (
    <div className="space-y-6">
      {/* 4 Core Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Monitored Websites */}
        <div 
          onClick={() => onNavigate('watchlist')}
          className="cursor-pointer group p-5 rounded-xl bg-navy-900/90 border border-navy-700/80 hover:border-teal-500/50 hover:bg-navy-900 transition-all shadow-lg shadow-black/20"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Active Monitored
            </span>
            <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Globe className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-white">
              {activeWebsitesCount}
            </span>
            <span className="text-xs text-slate-400">/ {websites.length} total URLs</span>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-teal-400/90 pt-3 border-t border-navy-800">
            <span className="flex items-center gap-1 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
              Continuous polling
            </span>
            <ArrowUpRight className="w-4 h-4 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
        </div>

        {/* Card 2: Changes Detected */}
        <div 
          onClick={() => onNavigate('history')}
          className="cursor-pointer group p-5 rounded-xl bg-navy-900/90 border border-navy-700/80 hover:border-teal-500/50 hover:bg-navy-900 transition-all shadow-lg shadow-black/20"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Changes Detected
            </span>
            <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center group-hover:scale-105 transition-transform">
              <History className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-white">
              {changes.length}
            </span>
            {unreadChanges.length > 0 && (
              <Badge variant="teal" size="sm">
                {unreadChanges.length} unreviewed
              </Badge>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-navy-800">
            <span>difflib text verification</span>
            <ArrowUpRight className="w-4 h-4 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
        </div>

        {/* Card 3: Upcoming Deadlines */}
        <div 
          onClick={() => onNavigate('deadlines')}
          className="cursor-pointer group p-5 rounded-xl bg-navy-900/90 border border-navy-700/80 hover:border-amber-500/50 hover:bg-navy-900 transition-all shadow-lg shadow-black/20"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Upcoming Deadlines
            </span>
            <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center group-hover:scale-105 transition-transform">
              <CalendarClock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-white">
              {deadlines.length}
            </span>
            {criticalDeadlines.length > 0 && (
              <Badge variant="rose" size="sm" dot>
                {criticalDeadlines.length} urgent
              </Badge>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-amber-400/90 pt-3 border-t border-navy-800">
            <span>Next in {deadlines[0]?.days_left ?? 0} days</span>
            <ArrowUpRight className="w-4 h-4 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
        </div>

        {/* Card 4: Recent Notifications */}
        <div 
          onClick={() => onNavigate('notifications')}
          className="cursor-pointer group p-5 rounded-xl bg-navy-900/90 border border-navy-700/80 hover:border-teal-500/50 hover:bg-navy-900 transition-all shadow-lg shadow-black/20"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Notifications
            </span>
            <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 text-teal-400 flex items-center justify-center group-hover:scale-105 transition-transform">
              <Bell className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-white">
              {notifications.length}
            </span>
            {unreadNotifications.length > 0 && (
              <Badge variant="teal" size="sm">
                {unreadNotifications.length} unread
              </Badge>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-navy-800">
            <span>Latest: {notifications[0]?.timestamp || 'None'}</span>
            <ArrowUpRight className="w-4 h-4 opacity-70 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </div>
        </div>
      </div>

      {/* Urgency Alert Banner if Critical Deadlines Exist */}
      {criticalDeadlines.length > 0 && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-md shadow-rose-950/20">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-rose-500/20 text-rose-300">
              <Flame className="w-5 h-5 text-rose-400 animate-pulse" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                Deadline Alert: {criticalDeadlines[0].title}
                <Badge variant="rose" size="sm">Due in {criticalDeadlines[0].days_left} Days</Badge>
              </h4>
              <p className="text-xs text-rose-200/80 mt-0.5">
                {criticalDeadlines[0].description || 'Approaching final cutoff date. Action required.'}
              </p>
            </div>
          </div>
          <button
            onClick={() => onNavigate('deadlines')}
            className="self-end sm:self-center px-3.5 py-1.5 rounded-lg bg-rose-500 hover:bg-rose-400 text-navy-950 text-xs font-bold transition-colors flex items-center gap-1.5 whitespace-nowrap"
          >
            Inspect Deadlines
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Split Section: Featured Recent Diff & Upcoming Deadlines */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Latest Detected Content Change */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white tracking-tight">
                Latest Content Change Detected
              </h3>
              <Badge variant="teal" size="sm">Real-time Diff</Badge>
            </div>
            <button
              onClick={() => onNavigate('history')}
              className="text-xs font-semibold text-teal-400 hover:text-teal-300 flex items-center gap-1 transition-colors"
            >
              View Full History
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {featuredChange ? (
            <div className="space-y-3">
              <div className="p-4 rounded-xl bg-navy-900/90 border border-navy-700/80">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-sm text-white">
                      {featuredChange.website_name}
                    </span>
                    <Badge variant="teal" size="sm">
                      {featuredChange.change_type}
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    {featuredChange.detected_at}
                  </span>
                </div>
                <p className="text-sm text-slate-300 font-medium mb-3">
                  {featuredChange.summary}
                </p>

                {/* Diff Viewer Component */}
                <DiffViewer
                  oldText={featuredChange.old_content_snippet}
                  newText={featuredChange.new_content_snippet}
                  websiteName={featuredChange.website_name}
                  detectedAt={featuredChange.detected_at}
                  additionsCount={featuredChange.additions_count}
                  deletionsCount={featuredChange.deletions_count}
                />
              </div>
            </div>
          ) : (
            <Card>
              <p className="text-sm text-slate-400 text-center py-6">
                No content changes detected yet. ChangeRadar is continuously polling watched targets.
              </p>
            </Card>
          )}
        </div>

        {/* Right 1 Col: Urgent Deadlines & Watched Targets Snapshot */}
        <div className="space-y-6">
          {/* Upcoming Deadlines Widget */}
          <Card
            title="Deadlines Radar"
            subtitle="Extracted university & course milestones"
            action={
              <button
                onClick={() => onNavigate('deadlines')}
                className="text-xs text-teal-400 hover:text-teal-300 font-semibold"
              >
                All ({deadlines.length})
              </button>
            }
          >
            <div className="space-y-3">
              {deadlines.slice(0, 4).map((d) => (
                <div
                  key={d.id}
                  className="p-3 rounded-lg bg-navy-950/70 border border-navy-800 hover:border-navy-700 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h5 className="text-xs font-semibold text-white leading-tight">
                      {d.title}
                    </h5>
                    <Badge
                      variant={d.days_left <= 3 ? 'rose' : d.days_left <= 7 ? 'amber' : 'teal'}
                      size="sm"
                    >
                      {d.days_left}d left
                    </Badge>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {d.due_date}
                    </span>
                    <a
                      href={d.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-teal-400/90 hover:text-teal-300 flex items-center gap-1"
                    >
                      Source
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Monitored Websites Quick Summary */}
          <Card
            title="Monitored Targets"
            subtitle="Active polling endpoints"
            action={
              <button
                onClick={onOpenAddModal}
                className="p-1 rounded-lg bg-teal-500/20 text-teal-300 hover:bg-teal-500/30 transition-colors"
                title="Add new website"
              >
                <Plus className="w-4 h-4" />
              </button>
            }
          >
            <div className="space-y-2.5">
              {websites.slice(0, 4).map((site) => (
                <div
                  key={site.id}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-navy-950/60 border border-navy-800 text-xs"
                >
                  <div className="truncate mr-2">
                    <div className="font-medium text-slate-200 truncate">{site.name}</div>
                    <div className="text-[11px] text-slate-400 truncate">{site.url}</div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-[11px] font-mono text-slate-400">
                      {site.check_interval_minutes}m
                    </span>
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
