/**
 * Utility functions for formatting dates and numbers cleanly across ChangeRadar UI.
 */

export function formatDateTime(dateStr?: string | null): string {
  if (!dateStr) return 'Just now';

  // If it's already a friendly relative string like "Just now", return as-is
  if (dateStr.includes('ago') || dateStr.toLowerCase() === 'just now') {
    return dateStr;
  }

  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return dateStr;
    }

    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffSeconds < 60) {
      return 'Just now';
    }
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) {
      return `${diffMinutes} min${diffMinutes > 1 ? 's' : ''} ago`;
    }
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    }
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}
