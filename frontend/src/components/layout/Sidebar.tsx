import React from 'react';
import { 
  Radar, 
  LayoutDashboard, 
  Globe, 
  History, 
  CalendarClock, 
  Bell, 
  Settings,
  X,
  Server,
  LogIn,
  LogOut
} from 'lucide-react';
import type { NavigationTab, UserProfile } from '../../types';

interface SidebarProps {
  activeTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  unreadCount?: number;
  criticalDeadlinesCount?: number;
  isBackendConnected: boolean;
  isDemoMode: boolean;
  currentUser?: UserProfile | null;
  onLogout?: () => void;
  onOpenAuthModal?: () => void;
}


export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  isOpenMobile,
  onCloseMobile,
  unreadCount = 0,
  criticalDeadlinesCount = 0,
  isBackendConnected,
  isDemoMode,
  currentUser,
  onLogout,
  onOpenAuthModal,
}) => {

  const navItems = [
    {
      id: 'dashboard' as NavigationTab,
      label: 'Dashboard',
      icon: LayoutDashboard,
    },
    {
      id: 'watchlist' as NavigationTab,
      label: 'Monitored Websites',
      icon: Globe,
    },
    {
      id: 'history' as NavigationTab,
      label: 'Change History',
      icon: History,
    },
    {
      id: 'deadlines' as NavigationTab,
      label: 'Deadlines',
      icon: CalendarClock,
      badge: criticalDeadlinesCount > 0 ? `${criticalDeadlinesCount}` : undefined,
      badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/40',
    },
    {
      id: 'notifications' as NavigationTab,
      label: 'Notifications',
      icon: Bell,
      badge: unreadCount > 0 ? `${unreadCount}` : undefined,
      badgeColor: 'bg-teal-500/20 text-teal-300 border-teal-500/40',
    },
    {
      id: 'settings' as NavigationTab,
      label: 'Settings',
      icon: Settings,
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 w-64 bg-navy-900 border-r border-navy-800 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Logo & Title */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-navy-800">
          <div className="flex items-center gap-3">
            <div className="relative flex items-center justify-center w-9 h-9 rounded-xl bg-teal-500/10 border border-teal-500/30 text-teal-400">
              <Radar className="w-5 h-5 animate-spin" style={{ animationDuration: '8s' }} />
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-teal-400 animate-ping" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                Change<span className="text-teal-400">Radar</span>
              </h1>
              <span className="text-[10px] tracking-widest uppercase font-mono text-teal-500/80">
                Webpage Sentinel
              </span>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          <div className="px-3 pb-2 text-[10px] uppercase font-bold tracking-wider text-slate-400">
            Navigation
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onTabChange(item.id);
                  onCloseMobile();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                  isActive
                    ? 'bg-teal-500/15 text-teal-300 border border-teal-500/30 shadow-sm shadow-teal-500/10'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-navy-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-teal-400' : 'text-slate-400 group-hover:text-slate-200'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${item.badgeColor}`}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* User Account Bar & Logout */}
        {currentUser ? (
          <div className="p-3 border-t border-navy-800">
            <div className="p-2.5 rounded-xl bg-navy-950/70 border border-navy-800 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 overflow-hidden">
                <div className="w-8 h-8 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400 flex items-center justify-center font-bold text-xs shrink-0">
                  {currentUser.name.charAt(0).toUpperCase()}
                </div>
                <div className="overflow-hidden">
                  <div className="text-xs font-bold text-white truncate">{currentUser.name}</div>
                  <div className="text-[10px] text-slate-400 truncate">{currentUser.email}</div>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Log out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <div className="p-3 border-t border-navy-800">
            <button
              onClick={onOpenAuthModal}
              className="w-full py-2 px-3 rounded-xl bg-teal-500/15 border border-teal-500/30 hover:bg-teal-500/25 text-teal-300 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
            >
              <LogIn className="w-4 h-4" />
              <span>Sign In / Register</span>
            </button>
          </div>
        )}

        {/* Backend & Environment Status Card */}
        <div className="p-3 pt-0">
          <div className="p-2.5 rounded-xl bg-navy-950/70 border border-navy-800/80 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Server className="w-3 h-3 text-teal-400" />
                Backend Status
              </span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isBackendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
            </div>

            <div className="text-[11px] text-slate-400">
              {isBackendConnected ? (
                <span className="text-emerald-400 font-medium">FastAPI Service Connected</span>
              ) : isDemoMode ? (
                <span className="text-amber-300 font-medium">Demo Data Mode Active</span>
              ) : (
                <span className="text-slate-400">Offline (Standby)</span>
              )}
            </div>
          </div>
        </div>
      </aside>

    </>
  );
};
