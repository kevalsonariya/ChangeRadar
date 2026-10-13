import React from 'react';
import {
  Menu,
  Search,
  Plus,
  Bell,
  RefreshCw,
  Radio
} from 'lucide-react';
import type { NavigationTab } from '../../types';

interface NavbarProps {
  activeTab: NavigationTab;
  onOpenMobile: () => void;
  onOpenAddModal: () => void;
  onNavigateNotifications: () => void;
  unreadCount?: number;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onRefreshAll: () => void;
  isRefreshing: boolean;
  isBackendConnected: boolean;
  isDemoMode: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onOpenMobile,
  onOpenAddModal,
  onNavigateNotifications,
  unreadCount = 0,
  searchQuery,
  onSearchChange,
  onRefreshAll,
  isRefreshing,
  isBackendConnected,
  isDemoMode,
}) => {
  const titles: Record<NavigationTab, { title: string; subtitle: string }> = {
    dashboard: {
      title: 'Command Center',
      subtitle: 'Real-time overview of tracked public resources & change triggers',
    },
    watchlist: {
      title: 'Monitored Websites',
      subtitle: 'Manage target web pages, polling intervals, and selectors',
    },
    history: {
      title: 'Change History',
      subtitle: 'Audit log of detected webpage content diffs and modifications',
    },
    deadlines: {
      title: 'Deadlines & Key Dates',
      subtitle: 'Extracted exam dates, submission cutoffs, and critical milestones',
    },
    notifications: {
      title: 'System Notifications',
      subtitle: 'Alerts generated from monitored page modifications and schedule shifts',
    },
    settings: {
      title: 'System Settings',
      subtitle: 'Scraper engine configurations, poll intervals, and API endpoints',
    },
  };

  const { title, subtitle } = titles[activeTab] || titles.dashboard;

  return (
    <header className="sticky top-0 z-30 h-16 bg-navy-950/80 backdrop-blur-md border-b border-navy-800/80 px-4 sm:px-6 flex items-center justify-between">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div>
          <h2 className="text-base sm:text-lg font-bold text-white tracking-tight flex items-center gap-2">
            {title}
            {isDemoMode && !isBackendConnected && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-amber-500/10 text-amber-300 border border-amber-500/30">
                <Radio className="w-2.5 h-2.5 animate-pulse" />
                Demo Mode
              </span>
            )}
          </h2>
          <p className="hidden md:block text-xs text-slate-400 font-normal">
            {subtitle}
          </p>
        </div>
      </div>

      {/* Right: Search, Refresh, Add Website, Notifications */}
      <div className="flex items-center gap-2.5 sm:gap-3">
        {/* Global Search Bar */}
        <div className="relative hidden md:block w-48 lg:w-64">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search targets, diffs..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-navy-900 border border-navy-700/80 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-teal-400 focus:ring-1 focus:ring-teal-400 transition-colors"
          />
        </div>

        {/* Check / Refresh Button */}
        <button
          onClick={onRefreshAll}
          disabled={isRefreshing}
          className="p-2 sm:px-3 sm:py-1.5 rounded-lg border border-navy-700/80 hover:border-slate-600 bg-navy-900 text-slate-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors active:scale-95 disabled:opacity-60"
          title="Trigger polling check on all active websites"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-teal-400 ${isRefreshing ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">{isRefreshing ? 'Checking...' : 'Poll Now'}</span>
        </button>

        {/* Quick Add Website */}
        <button
          onClick={onOpenAddModal}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold shadow-md shadow-teal-500/20 transition-colors active:scale-95"
        >
          <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
          <span className="hidden xs:inline">Add Website</span>
        </button>

        {/* Notification Bell */}
        <button
          onClick={onNavigateNotifications}
          className="relative p-2 rounded-lg border border-navy-700/80 hover:border-slate-600 bg-navy-900 text-slate-300 hover:text-white transition-colors"
          title="View notifications"
        >
          <Bell className="w-4 h-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-teal-500 px-1 text-[10px] font-bold text-navy-950">
              {unreadCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
};
