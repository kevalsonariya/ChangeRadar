import { useState, useEffect, useCallback } from 'react';
import type { NavigationTab, MonitoredWebsite, ChangeRecord, DeadlineItem, NotificationItem } from './types';
import {
  MOCK_WEBSITES,
  MOCK_CHANGES,
  MOCK_DEADLINES,
  MOCK_NOTIFICATIONS
} from './data/mockData';
import {
  checkBackendHealth,
  fetchWebsitesApi,
  createWebsiteApi,
  deleteWebsiteApi,
  fetchChangesApi,
  fetchDeadlinesApi,
  fetchNotificationsApi
} from './services/api';

import { Sidebar } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { AddWebsiteModal } from './components/modals/AddWebsiteModal';

import { DashboardView } from './pages/DashboardView';
import { WatchlistView } from './pages/WatchlistView';
import { ChangeHistoryView } from './pages/ChangeHistoryView';
import { DeadlinesView } from './pages/DeadlinesView';
import { NotificationsView } from './pages/NotificationsView';
import { SettingsView } from './pages/SettingsView';

export function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>('dashboard');
  const [isOpenMobile, setIsOpenMobile] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Data states
  const [websites, setWebsites] = useState<MonitoredWebsite[]>(MOCK_WEBSITES);
  const [changes, setChanges] = useState<ChangeRecord[]>(MOCK_CHANGES);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>(MOCK_DEADLINES);
  const [notifications, setNotifications] = useState<NotificationItem[]>(MOCK_NOTIFICATIONS);

  // Connection & Demo Mode states
  const [isDemoMode, setIsDemoMode] = useState<boolean>(true);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [isTestingConnection, setIsTestingConnection] = useState<boolean>(false);
  const [backendError, setBackendError] = useState<string | null>(null);

  // In-flight polling action
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [checkingId, setCheckingId] = useState<number | null>(null);

  // Check backend health on initial mount
  const testBackendConnection = useCallback(async () => {
    setIsTestingConnection(true);
    setBackendError(null);
    try {
      const health = await checkBackendHealth();
      if (health.success && health.data?.status === 'healthy') {
        setIsBackendConnected(true);

        // Fetch live data from backend
        const [sitesRes, changesRes, deadlinesRes, notifsRes] = await Promise.all([
          fetchWebsitesApi(),
          fetchChangesApi(),
          fetchDeadlinesApi(),
          fetchNotificationsApi(),
        ]);

        if (sitesRes.success && sitesRes.data) setWebsites(sitesRes.data);
        if (changesRes.success && changesRes.data) setChanges(changesRes.data);
        if (deadlinesRes.success && deadlinesRes.data) setDeadlines(deadlinesRes.data);
        if (notifsRes.success && notifsRes.data) setNotifications(notifsRes.data);

        setIsDemoMode(false);
      } else {
        setIsBackendConnected(false);
        setBackendError(health.error || 'FastAPI backend is offline.');
      }
    } catch (err) {
      setIsBackendConnected(false);
      setBackendError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setIsTestingConnection(false);
    }
  }, []);

  useEffect(() => {
    testBackendConnection();
  }, [testBackendConnection]);

  // Handle Demo Mode switch
  const handleToggleDemoMode = (enabled: boolean) => {
    setIsDemoMode(enabled);
    if (enabled) {
      setWebsites(MOCK_WEBSITES);
      setChanges(MOCK_CHANGES);
      setDeadlines(MOCK_DEADLINES);
      setNotifications(MOCK_NOTIFICATIONS);
    } else {
      testBackendConnection();
    }
  };

  // Add website action
  const handleAddWebsite = async (newSiteData: {
    name: string;
    url: string;
    category: string;
    selector?: string;
    check_interval_minutes: number;
  }) => {
    if (isBackendConnected && !isDemoMode) {
      const result = await createWebsiteApi(newSiteData);
      if (result.success && result.data) {
        setWebsites(prev => [result.data!, ...prev]);
      }
    } else {
      const newSite: MonitoredWebsite = {
        id: Date.now(),
        name: newSiteData.name,
        url: newSiteData.url,
        category: newSiteData.category,
        selector: newSiteData.selector,
        check_interval_minutes: newSiteData.check_interval_minutes,
        status: 'active',
        last_checked_at: 'Just now',
        last_change_at: undefined,
        change_count: 0,
        created_at: new Date().toISOString().split('T')[0],
      };
      setWebsites(prev => [newSite, ...prev]);

      // Add a notification
      const newNotif: NotificationItem = {
        id: Date.now(),
        type: 'system',
        title: 'New Webpage Monitored',
        message: `ChangeRadar is now tracking "${newSite.name}" every ${newSite.check_interval_minutes} minutes.`,
        timestamp: 'Just now',
        is_read: false,
        target_url: newSite.url,
      };
      setNotifications(prev => [newNotif, ...prev]);
    }
  };

  // Delete website
  const handleDeleteWebsite = async (id: number) => {
    if (isBackendConnected && !isDemoMode) {
      await deleteWebsiteApi(id);
    }
    setWebsites(prev => prev.filter(w => w.id !== id));
  };

  // Check / Poll single website
  const handleCheckWebsite = (id: number) => {
    setCheckingId(id);
    setTimeout(() => {
      setWebsites(prev =>
        prev.map(w =>
          w.id === id ? { ...w, last_checked_at: 'Just now' } : w
        )
      );
      setCheckingId(null);
    }, 1200);
  };

  // Refresh all
  const handleRefreshAll = () => {
    setIsRefreshing(true);
    setTimeout(() => {
      setWebsites(prev =>
        prev.map(w => ({ ...w, last_checked_at: 'Just now' }))
      );
      setIsRefreshing(false);
    }, 1500);
  };

  // Mark single change as read
  const handleMarkChangeRead = (id: number) => {
    setChanges(prev =>
      prev.map(c => (c.id === id ? { ...c, is_read: true } : c))
    );
  };

  // Mark all changes as read
  const handleMarkAllChangesRead = () => {
    setChanges(prev => prev.map(c => ({ ...c, is_read: true })));
  };

  // Add deadline
  const handleAddDeadline = (newD: Omit<DeadlineItem, 'id'>) => {
    const item: DeadlineItem = {
      ...newD,
      id: Date.now(),
    };
    setDeadlines(prev => [item, ...prev]);
  };

  // Notifications read handlers
  const handleMarkNotifRead = (id: number) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, is_read: true } : n))
    );
  };

  const handleMarkAllNotifsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
  };

  const unreadNotificationsCount = notifications.filter(n => !n.is_read).length;
  const criticalDeadlinesCount = deadlines.filter(d => d.status === 'critical' || d.days_left <= 3).length;

  return (
    <div className="min-h-screen bg-navy-950 text-slate-100 flex flex-col font-sans">
      {/* Responsive Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={setActiveTab}
        isOpenMobile={isOpenMobile}
        onCloseMobile={() => setIsOpenMobile(false)}
        unreadCount={unreadNotificationsCount}
        criticalDeadlinesCount={criticalDeadlinesCount}
        isBackendConnected={isBackendConnected}
        isDemoMode={isDemoMode}
      />

      {/* Main Content Area */}
      <div className="lg:pl-64 flex flex-col flex-1 min-w-0">
        <Navbar
          activeTab={activeTab}
          onOpenMobile={() => setIsOpenMobile(true)}
          onOpenAddModal={() => setIsAddModalOpen(true)}
          onNavigateNotifications={() => setActiveTab('notifications')}
          unreadCount={unreadNotificationsCount}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onRefreshAll={handleRefreshAll}
          isRefreshing={isRefreshing}
          isBackendConnected={isBackendConnected}
          isDemoMode={isDemoMode}
        />

        {/* Page Container */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {activeTab === 'dashboard' && (
            <DashboardView
              websites={websites}
              changes={changes}
              deadlines={deadlines}
              notifications={notifications}
              onNavigate={setActiveTab}
              onOpenAddModal={() => setIsAddModalOpen(true)}
              onRefreshAll={handleRefreshAll}
              isRefreshing={isRefreshing}
            />
          )}

          {activeTab === 'watchlist' && (
            <WatchlistView
              websites={websites}
              onOpenAddModal={() => setIsAddModalOpen(true)}
              onDeleteWebsite={handleDeleteWebsite}
              onCheckWebsite={handleCheckWebsite}
              checkingId={checkingId}
            />
          )}

          {activeTab === 'history' && (
            <ChangeHistoryView
              changes={changes}
              onMarkAsRead={handleMarkChangeRead}
              onMarkAllAsRead={handleMarkAllChangesRead}
            />
          )}

          {activeTab === 'deadlines' && (
            <DeadlinesView
              deadlines={deadlines}
              onAddDeadline={handleAddDeadline}
            />
          )}

          {activeTab === 'notifications' && (
            <NotificationsView
              notifications={notifications}
              onMarkAsRead={handleMarkNotifRead}
              onMarkAllAsRead={handleMarkAllNotifsRead}
            />
          )}

          {activeTab === 'settings' && (
            <SettingsView
              isBackendConnected={isBackendConnected}
              isDemoMode={isDemoMode}
              onToggleDemoMode={handleToggleDemoMode}
              onTestBackendConnection={testBackendConnection}
              isTestingConnection={isTestingConnection}
              backendError={backendError}
            />
          )}
        </main>
      </div>

      {/* Add Website Modal Dialog */}
      <AddWebsiteModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddWebsite}
      />
    </div>
  );
}

export default App;
