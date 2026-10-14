import React, { useState } from 'react';
import { 
  Bell, 
  CheckCheck, 
  ExternalLink, 
  Flame, 
  History, 
  CheckCircle2, 
  Clock,
  Radio
} from 'lucide-react';
import type { NotificationItem } from '../types';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';
import { formatDateTime } from '../utils/formatters';

interface NotificationsViewProps {
  notifications: NotificationItem[];
  onMarkAsRead: (id: number) => void;
  onMarkAllAsRead: () => void;
}

export const NotificationsView: React.FC<NotificationsViewProps> = ({
  notifications,
  onMarkAsRead,
  onMarkAllAsRead,
}) => {
  const [filterType, setFilterType] = useState<string>('all');

  const filteredNotifications = notifications.filter((n) => {
    if (filterType === 'all') return true;
    return n.type === filterType;
  });

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="space-y-6">
      {/* Top Filter Buttons & Mark All Read */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: 'all', label: 'All Alerts' },
            { id: 'change', label: 'Content Changes' },
            { id: 'deadline', label: 'Deadline Warnings' },
            { id: 'system', label: 'System Logs' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterType(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                filterType === tab.id
                  ? 'bg-teal-500 text-navy-950 shadow-md shadow-teal-500/20'
                  : 'bg-navy-900 border border-navy-700/80 text-slate-300 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {unreadCount > 0 && (
          <button
            onClick={onMarkAllAsRead}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-teal-500/40 bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 text-xs font-semibold transition-colors whitespace-nowrap self-end sm:self-center"
          >
            <CheckCheck className="w-3.5 h-3.5" />
            Mark All as Read ({unreadCount})
          </button>
        )}
      </div>

      {/* Notifications List */}
      {filteredNotifications.length > 0 ? (
        <div className="space-y-3">
          {filteredNotifications.map((notif) => {
            return (
              <div
                key={notif.id}
                className={`p-4 sm:p-5 rounded-xl border transition-all shadow-md flex items-start justify-between gap-4 ${
                  notif.is_read
                    ? 'bg-navy-900/60 border-navy-800'
                    : 'bg-navy-900/90 border-teal-500/40 shadow-teal-950/20'
                }`}
              >
                <div className="flex items-start gap-3.5">
                  <div
                    className={`p-2.5 rounded-xl border mt-0.5 flex-shrink-0 ${
                      notif.type === 'change'
                        ? 'bg-teal-500/10 border-teal-500/30 text-teal-400'
                        : notif.type === 'deadline'
                        ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                        : 'bg-slate-800 border-slate-700 text-slate-300'
                    }`}
                  >
                    {notif.type === 'change' ? (
                      <History className="w-4 h-4" />
                    ) : notif.type === 'deadline' ? (
                      <Flame className="w-4 h-4" />
                    ) : (
                      <Radio className="w-4 h-4" />
                    )}
                  </div>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="text-sm font-bold text-white">
                        {notif.title}
                      </h4>
                      <Badge
                        variant={
                          notif.type === 'change'
                            ? 'teal'
                            : notif.type === 'deadline'
                            ? 'rose'
                            : 'slate'
                        }
                        size="sm"
                      >
                        {notif.type}
                      </Badge>
                      {!notif.is_read && (
                        <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
                      )}
                    </div>

                    <p className="text-xs text-slate-300 leading-relaxed">
                      {notif.message}
                    </p>

                    <div className="flex items-center gap-3 pt-1 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {formatDateTime(notif.created_at)}
                      </span>
                      {notif.target_url && (
                        <a
                          href={notif.target_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-teal-400 hover:text-teal-300 inline-flex items-center gap-1 font-medium"
                        >
                          Target Link
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>

                {!notif.is_read && (
                  <button
                    onClick={() => onMarkAsRead(notif.id)}
                    className="p-1.5 rounded-lg border border-navy-700 hover:border-slate-600 bg-navy-800 text-slate-400 hover:text-white transition-colors flex-shrink-0"
                    title="Mark as read"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={Bell}
          title="No Notifications in Feed"
          description="You are completely caught up! New notifications trigger whenever monitored sites experience content changes."
        />
      )}
    </div>
  );
};
