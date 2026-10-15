import { useState, useEffect, useCallback } from 'react';
import type { NavigationTab, MonitoredWebsite, ChangeRecord, DeadlineItem, DeadlinePriority, NotificationItem, UserProfile } from './types';
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
  checkWebsiteApi,
  fetchChangesApi,
  markChangeReadApi,
  fetchDeadlinesApi,
  createDeadlineApi,
  updateDeadlineApi,
  toggleDeadlineCompleteApi,
  deleteDeadlineApi,
  fetchNotificationsApi,
  markNotificationReadApi,
  markAllNotificationsReadApi,
  getMeApi,
  logoutApi,
  updateSettingsApi,
  verifyEmailApi,
  resendVerificationApi
} from './services/api';

import { Sidebar } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { AddWebsiteModal } from './components/modals/AddWebsiteModal';
import { AuthModal } from './components/modals/AuthModal';

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

  // Data states (Starts fresh and empty for real user data)
  const [websites, setWebsites] = useState<MonitoredWebsite[]>([]);
  const [changes, setChanges] = useState<ChangeRecord[]>([]);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  // Connection & Demo Mode states
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);
  const [isTestingConnection, setIsTestingConnection] = useState<boolean>(false);

  const [backendError, setBackendError] = useState<string | null>(null);

  // User & Auth State
  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);


  // In-flight polling action
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [operationFeedback, setOperationFeedback] = useState<{
    type: 'success' | 'info' | 'warning' | 'error';
    message: string;
    details?: string;
  } | null>(null);

  useEffect(() => {
    if (operationFeedback) {
      const timer = setTimeout(() => setOperationFeedback(null), 7000);
      return () => clearTimeout(timer);
    }
  }, [operationFeedback]);

  // Load authenticated user profile
  const checkAuth = useCallback(async () => {
    setIsCheckingAuth(true);
    try {
      const meRes = await getMeApi();
      if (meRes.success && meRes.data) {
        setCurrentUser(meRes.data);
      } else {
        setCurrentUser(null);
      }
    } catch {
      setCurrentUser(null);
    } finally {
      setIsCheckingAuth(false);
    }
  }, []);


  // Check URL query parameters for ?verify_token=xyz
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const verifyToken = params.get('verify_token');
    if (verifyToken) {
      verifyEmailApi(verifyToken).then((res) => {
        if (res.success) {
          setOperationFeedback({
            type: 'success',
            message: 'Email Verified Successfully!',
            details: 'Your account is now verified. ChangeRadar email notifications are fully enabled.'
          });
          checkAuth();
        } else {
          setOperationFeedback({
            type: 'error',
            message: 'Email Verification Failed',
            details: res.error || 'Token may be expired or invalid.'
          });
        }
        // Clean URL
        window.history.replaceState({}, document.title, window.location.pathname);
      });
    }
  }, [checkAuth]);

  // Check backend health & fetch user targets
  const testBackendConnection = useCallback(async () => {
    setIsTestingConnection(true);
    setBackendError(null);
    try {
      const health = await checkBackendHealth();
      if (health.success && health.data?.status === 'healthy') {
        setIsBackendConnected(true);

        // Fetch user session first
        await checkAuth();

        // Fetch live data from backend
        const [sitesRes, changesRes, deadlinesRes, notifsRes] = await Promise.all([
          fetchWebsitesApi(),
          fetchChangesApi(),
          fetchDeadlinesApi(),
          fetchNotificationsApi(),
        ]);

        setWebsites(sitesRes.success && sitesRes.data ? sitesRes.data : []);
        setChanges(changesRes.success && changesRes.data ? changesRes.data : []);
        setDeadlines(deadlinesRes.success && deadlinesRes.data ? deadlinesRes.data : []);
        setNotifications(notifsRes.success && notifsRes.data ? notifsRes.data : []);

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
  }, [checkAuth]);

  useEffect(() => {
    testBackendConnection();
  }, [testBackendConnection]);

  const handleLogout = async () => {
    await logoutApi();
    setCurrentUser(null);
    setOperationFeedback({
      type: 'info',
      message: 'Logged out successfully',
      details: 'You have been signed out of ChangeRadar.'
    });
    // Refresh websites / data
    testBackendConnection();
  };

  const handleAuthSuccess = (user: UserProfile) => {
    setCurrentUser(user);
    setIsAuthModalOpen(false);
    setOperationFeedback({
      type: 'success',
      message: `Welcome, ${user.name}!`,
      details: user.email_verified 
        ? 'Account authenticated and ready.' 
        : 'Please verify your email address to enable personalized email alerts.'
    });
    testBackendConnection();
  };

  const handleUpdateSettings = async (settings: { email_notifications_enabled?: boolean; name?: string }) => {
    const res = await updateSettingsApi(settings);
    if (res.success && res.data) {
      setCurrentUser(res.data);
      setOperationFeedback({
        type: 'success',
        message: 'Settings updated successfully',
        details: 'Your notification preferences have been saved.'
      });
    } else {
      setOperationFeedback({
        type: 'error',
        message: 'Failed to update settings',
        details: res.error
      });
    }
  };

  const handleResendVerification = async () => {
    const res = await resendVerificationApi();
    if (res.success) {
      setOperationFeedback({
        type: 'success',
        message: 'Verification Email Sent',
        details: res.data?.message || 'Check your inbox for the verification link.'
      });
    } else {
      setOperationFeedback({
        type: 'error',
        message: 'Could not send verification email',
        details: res.error
      });
    }
  };


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
  }): Promise<{ success: boolean; error?: string }> => {
    if (isBackendConnected && !isDemoMode) {
      const result = await createWebsiteApi(newSiteData);
      if (result.success && result.data) {
        setWebsites(prev => [result.data!, ...prev]);
        setOperationFeedback({
          type: 'success',
          message: `Added "${result.data.name}" to watchlist`,
          details: `ChangeRadar is now monitoring ${result.data.url}`
        });
        return { success: true };
      } else {
        return { success: false, error: result.error || 'Failed to register website.' };
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
        last_checked_at: new Date().toISOString(),
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
        created_at: new Date().toISOString(),
        is_read: false,
        target_url: newSite.url,
      };
      setNotifications(prev => [newNotif, ...prev]);
      setOperationFeedback({
        type: 'info',
        message: `Added "${newSite.name}" (Demonstration Mode)`,
        details: 'Connect the FastAPI backend to store records persistently in SQLite.'
      });
      return { success: true };
    }
  };

  // Delete website
  const handleDeleteWebsite = async (id: number) => {
    const site = websites.find(w => w.id === id);
    const siteName = site ? `"${site.name}"` : 'this website';
    const confirmed = window.confirm(
      `Are you sure you want to stop monitoring ${siteName}?\n\nAll captured snapshots, diff records, and associated change alerts will also be deleted.`
    );
    if (!confirmed) return;

    if (isBackendConnected && !isDemoMode) {
      const res = await deleteWebsiteApi(id);
      if (res.success) {
        setOperationFeedback({
          type: 'info',
          message: `Deleted ${siteName} from watchlist`,
          details: 'All related snapshots and detected diffs were purged.'
        });
        const [changesRes, notifsRes] = await Promise.all([
          fetchChangesApi(),
          fetchNotificationsApi(),
        ]);
        if (changesRes.success && changesRes.data) setChanges(changesRes.data);
        if (notifsRes.success && notifsRes.data) setNotifications(notifsRes.data);
      } else {
        setOperationFeedback({
          type: 'error',
          message: res.error || `Failed to delete ${siteName}.`
        });
        return;
      }
    } else {
      setOperationFeedback({
        type: 'info',
        message: `Removed ${siteName} from watchlist.`
      });
    }
    setWebsites(prev => prev.filter(w => w.id !== id));
    setChanges(prev => prev.filter(c => c.website_id !== id));
  };

  // Check / Poll single website
  const handleCheckWebsite = async (id: number) => {
    setCheckingId(id);
    setOperationFeedback(null);
    if (isBackendConnected && !isDemoMode) {
      const res = await checkWebsiteApi(id);
      if (res.success && res.data) {
        const checkResult = res.data;
        if (checkResult.status === 'baseline_created') {
          setOperationFeedback({
            type: 'success',
            message: 'Baseline Snapshot Captured',
            details: 'Initial content saved as baseline. Future checks will monitor for text differences.'
          });
        } else if (checkResult.status === 'no_change') {
          setOperationFeedback({
            type: 'info',
            message: 'Content Unchanged',
            details: 'No meaningful text changes detected since the previous snapshot.'
          });
        } else if (checkResult.status === 'change_detected') {
          setOperationFeedback({
            type: 'warning',
            message: 'Content Change Detected!',
            details: checkResult.message || 'New snapshot captured and diff logged in history.'
          });
        }

        const [sitesRes, changesRes, notifsRes] = await Promise.all([
          fetchWebsitesApi(),
          fetchChangesApi(),
          fetchNotificationsApi(),
        ]);
        if (sitesRes.success && sitesRes.data) setWebsites(sitesRes.data);
        if (changesRes.success && changesRes.data) setChanges(changesRes.data);
        if (notifsRes.success && notifsRes.data) setNotifications(notifsRes.data);
      } else {
        setOperationFeedback({
          type: 'error',
          message: 'Website Check Failed',
          details: res.error || 'Server returned an error during the webpage fetch.'
        });
        const sitesRes = await fetchWebsitesApi();
        if (sitesRes.success && sitesRes.data) setWebsites(sitesRes.data);
      }
    } else {
      setTimeout(() => {
        setWebsites(prev =>
          prev.map(w =>
            w.id === id ? { ...w, last_checked_at: 'Just now' } : w
          )
        );
        setOperationFeedback({
          type: 'info',
          message: 'Check Complete (Demonstration Mode)',
          details: 'Switch to live mode to perform actual HTTP fetching and diffing.'
        });
      }, 800);
    }
    setCheckingId(null);
  };

  // Refresh all
  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    setOperationFeedback(null);
    if (isBackendConnected && !isDemoMode) {
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
      setOperationFeedback({
        type: 'info',
        message: 'Watchlist & Deadlines Refreshed',
        details: 'Synchronized latest data from SQLite backend.'
      });
    } else {
      setTimeout(() => {
        setWebsites(prev =>
          prev.map(w => ({ ...w, last_checked_at: 'Just now' }))
        );
      }, 1000);
    }
    setIsRefreshing(false);
  };

  // Mark single change as read
  const handleMarkChangeRead = async (id: number) => {
    if (isBackendConnected && !isDemoMode) {
      await markChangeReadApi(id);
    }
    setChanges(prev =>
      prev.map(c => (c.id === id ? { ...c, is_read: true } : c))
    );
  };

  // Mark all changes as read
  const handleMarkAllChangesRead = async () => {
    if (isBackendConnected && !isDemoMode) {
      const unread = changes.filter(c => !c.is_read);
      await Promise.all(unread.map(c => markChangeReadApi(c.id)));
    }
    setChanges(prev => prev.map(c => ({ ...c, is_read: true })));
  };

  // Add deadline
  const handleAddDeadline = async (newD: {
    title: string;
    due_date: string;
    priority?: DeadlinePriority;
    category?: string;
    description?: string;
    source_url?: string;
  }): Promise<{ success: boolean; error?: string }> => {
    if (isBackendConnected && !isDemoMode) {
      const res = await createDeadlineApi(newD);
      if (res.success && res.data) {
        setDeadlines(prev => [res.data!, ...prev]);
        setOperationFeedback({
          type: 'success',
          message: `Added deadline "${res.data.title}"`,
          details: `Due on ${res.data.due_date} (${res.data.days_left} days left). Stored in SQLite.`
        });
        return { success: true };
      } else {
        return { success: false, error: res.error || 'Failed to create deadline.' };
      }
    } else {
      const item: DeadlineItem = {
        ...newD,
        id: Date.now(),
        priority: newD.priority || 'medium',
        category: newD.category || 'Academic',
        status: 'upcoming',
        days_left: 7,
        is_completed: false,
      };
      setDeadlines(prev => [item, ...prev]);
      setOperationFeedback({
        type: 'info',
        message: `Added deadline "${item.title}" (Demonstration Mode)`,
      });
      return { success: true };
    }
  };

  // Toggle deadline completion
  const handleToggleDeadlineComplete = async (id: number) => {
    const existing = deadlines.find(d => d.id === id);
    const targetStatus = !existing?.is_completed;
    if (isBackendConnected && !isDemoMode) {
      const res = await toggleDeadlineCompleteApi(id, targetStatus);
      if (res.success && res.data) {
        setDeadlines(prev => prev.map(d => (d.id === id ? res.data! : d)));
        setOperationFeedback({
          type: 'success',
          message: targetStatus ? 'Deadline marked as completed' : 'Deadline reopened',
          details: res.data.title
        });
      } else {
        setOperationFeedback({
          type: 'error',
          message: res.error || 'Failed to update deadline status'
        });
      }
    } else {
      setDeadlines(prev =>
        prev.map(d =>
          d.id === id
            ? {
                ...d,
                is_completed: targetStatus,
                status: targetStatus ? 'completed' : d.days_left <= 3 ? 'critical' : 'upcoming'
              }
            : d
        )
      );
    }
  };

  // Delete deadline
  const handleDeleteDeadline = async (id: number) => {
    const deadline = deadlines.find(d => d.id === id);
    const confirmed = window.confirm(
      `Delete deadline "${deadline?.title || 'this item'}"?\nThis cannot be undone.`
    );
    if (!confirmed) return;

    if (isBackendConnected && !isDemoMode) {
      const res = await deleteDeadlineApi(id);
      if (res.success) {
        setDeadlines(prev => prev.filter(d => d.id !== id));
        setOperationFeedback({
          type: 'info',
          message: 'Deadline deleted',
          details: deadline?.title
        });
      } else {
        setOperationFeedback({
          type: 'error',
          message: res.error || 'Failed to delete deadline'
        });
      }
    } else {
      setDeadlines(prev => prev.filter(d => d.id !== id));
    }
  };

  // Edit deadline
  const handleEditDeadline = async (
    id: number,
    payload: Partial<DeadlineItem>
  ): Promise<{ success: boolean; error?: string }> => {
    if (isBackendConnected && !isDemoMode) {
      const res = await updateDeadlineApi(id, payload);
      if (res.success && res.data) {
        setDeadlines(prev => prev.map(d => (d.id === id ? res.data! : d)));
        setOperationFeedback({
          type: 'success',
          message: 'Deadline updated successfully',
          details: res.data.title
        });
        return { success: true };
      } else {
        return { success: false, error: res.error || 'Failed to update deadline' };
      }
    } else {
      setDeadlines(prev => prev.map(d => (d.id === id ? { ...d, ...payload } : d)));
      return { success: true };
    }
  };

  // Notifications read handlers
  const handleMarkNotifRead = async (id: number) => {
    if (isBackendConnected && !isDemoMode) {
      const res = await markNotificationReadApi(id);
      if (res.success && res.data) {
        setNotifications(prev =>
          prev.map(n => (n.id === id ? res.data! : n))
        );
      } else {
        setOperationFeedback({
          type: 'error',
          message: res.error || 'Failed to mark notification as read'
        });
      }
    } else {
      setNotifications(prev =>
        prev.map(n => (n.id === id ? { ...n, is_read: true } : n))
      );
    }
  };

  const handleMarkAllNotifsRead = async () => {
    if (isBackendConnected && !isDemoMode) {
      const res = await markAllNotificationsReadApi();
      if (res.success) {
        setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
        setOperationFeedback({
          type: 'success',
          message: 'All notifications marked as read',
          details: `${res.data?.updated_count ?? 0} alerts updated.`
        });
      } else {
        setOperationFeedback({
          type: 'error',
          message: res.error || 'Failed to mark all as read'
        });
      }
    } else {
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
    }
  };

  const unreadNotificationsCount = notifications.filter(n => !n.is_read).length;
  const criticalDeadlinesCount = deadlines.filter(d => !d.is_completed && (d.status === 'critical' || d.days_left <= 3)).length;

  // 1. Initial auth verification loading spinner
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-navy-950 flex flex-col items-center justify-center text-slate-100 font-sans p-4">
        <div className="relative flex items-center justify-center w-16 h-16 rounded-2xl bg-teal-500/10 border border-teal-500/30 text-teal-400 mb-4 shadow-xl shadow-teal-500/10">
          <div className="w-8 h-8 border-3 border-teal-500 border-t-transparent rounded-full animate-spin" />
        </div>
        <h2 className="text-lg font-bold text-white tracking-tight">ChangeRadar</h2>
        <p className="text-xs text-slate-400 mt-1">Verifying secure session...</p>
      </div>
    );
  }

  // 2. Mandatory Authentication Gate: if user is not logged in, render mandatory AuthModal
  if (!currentUser) {
    return (
      <div className="min-h-screen bg-navy-950 flex flex-col justify-between font-sans relative overflow-hidden">
        {/* Ambient background decoration */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-10 left-10 w-72 h-72 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Top brand header */}
        <header className="p-6 flex items-center justify-between max-w-6xl w-full mx-auto relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center justify-center text-teal-400 font-bold">
              CR
            </div>
            <span className="text-lg font-bold text-white tracking-tight">
              Change<span className="text-teal-400">Radar</span>
            </span>
          </div>
          <div className="text-xs text-slate-400">
            Secure Webpage Sentinel
          </div>
        </header>

        {/* Center content banner */}
        <main className="flex-1 flex flex-col items-center justify-center text-center p-6 relative z-10 max-w-xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-300 text-xs font-semibold mb-4">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse" />
            Authentication Required
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
            Monitor webpage changes and deadlines in real time.
          </h1>
          <p className="text-sm text-slate-400 mt-3 max-w-md">
            Please sign in or register an account to access your personal dashboard, watchlists, diff history, and personalized alert delivery.
          </p>

          <button
            onClick={() => setIsAuthModalOpen(true)}
            className="mt-6 px-6 py-3 rounded-xl bg-teal-500 hover:bg-teal-400 text-navy-950 font-bold text-xs uppercase tracking-wider shadow-lg shadow-teal-500/20 transition-all hover:scale-105 active:scale-95"
          >
            Sign In / Register
          </button>
        </main>

        {/* Footer */}
        <footer className="p-6 text-center text-xs text-slate-500 relative z-10 border-t border-navy-900">
          ChangeRadar &bull; College 5th Semester SGP &bull; Fast, Secure, Automated Monitoring
        </footer>

        {/* Mandatory Authentication Modal Dialog */}
        <AuthModal
          isOpen={true}
          isMandatory={true}
          onSuccess={handleAuthSuccess}
        />
      </div>
    );
  }

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
        currentUser={currentUser}
        onLogout={handleLogout}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
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
          {/* Real-time Operation Feedback Banner */}
          {operationFeedback && (
            <div
              className={`mb-6 p-4 rounded-xl border flex items-start justify-between gap-3 shadow-lg transition-all animate-in fade-in duration-200 ${
                operationFeedback.type === 'success'
                  ? 'bg-teal-950/50 border-teal-500/50 text-teal-200'
                  : operationFeedback.type === 'warning'
                  ? 'bg-amber-950/50 border-amber-500/50 text-amber-200'
                  : operationFeedback.type === 'error'
                  ? 'bg-rose-950/50 border-rose-500/50 text-rose-200'
                  : 'bg-navy-900 border-navy-700 text-slate-200'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-base select-none leading-none mt-0.5">
                  {operationFeedback.type === 'success' && '✓'}
                  {operationFeedback.type === 'warning' && '⚡'}
                  {operationFeedback.type === 'error' && '✕'}
                  {operationFeedback.type === 'info' && 'ℹ'}
                </span>
                <div>
                  <p className="text-xs sm:text-sm font-semibold text-white">{operationFeedback.message}</p>
                  {operationFeedback.details && (
                    <p className="text-xs opacity-90 mt-0.5 font-mono">{operationFeedback.details}</p>
                  )}
                </div>
              </div>
              <button
                onClick={() => setOperationFeedback(null)}
                className="text-slate-400 hover:text-white text-xs font-bold px-2 py-1 rounded hover:bg-white/10 transition-colors"
                title="Dismiss banner"
              >
                ✕
              </button>
            </div>
          )}

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
              onToggleComplete={handleToggleDeadlineComplete}
              onDeleteDeadline={handleDeleteDeadline}
              onEditDeadline={handleEditDeadline}
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
              currentUser={currentUser}
              onUpdateSettings={handleUpdateSettings}
              onResendVerification={handleResendVerification}
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

      {/* Authentication Modal Dialog */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={handleAuthSuccess}
      />
    </div>
  );
}

export default App;

