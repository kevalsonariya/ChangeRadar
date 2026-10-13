import React, { useState } from 'react';
import { 
  History, 
  Search, 
  Filter, 
  Calendar, 
  CheckCheck, 
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import type { ChangeRecord } from '../types';
import { Badge } from '../components/common/Badge';
import { DiffViewer } from '../components/common/DiffViewer';
import { EmptyState } from '../components/common/EmptyState';

interface ChangeHistoryViewProps {
  changes: ChangeRecord[];
  onMarkAsRead: (id: number) => void;
  onMarkAllAsRead: () => void;
}

export const ChangeHistoryView: React.FC<ChangeHistoryViewProps> = ({
  changes,
  onMarkAsRead,
  onMarkAllAsRead,
}) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedIds, setExpandedIds] = useState<Record<number, boolean>>({
    // Auto-expand the most recent one
    [changes[0]?.id || 0]: true,
  });

  const toggleExpand = (id: number) => {
    setExpandedIds(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredChanges = changes.filter((change) => {
    const matchesType = filterType === 'all' || change.change_type === filterType;
    const matchesSearch =
      change.website_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      change.summary.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const unreadCount = changes.filter(c => !c.is_read).length;

  return (
    <div className="space-y-6">
      {/* Top Controls: Filter Types, Search, Mark All Read */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Type Filter Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          <Filter className="w-4 h-4 text-slate-500 mr-1 flex-shrink-0" />
          {[
            { id: 'all', label: 'All Diffs' },
            { id: 'modification', label: 'Modifications' },
            { id: 'addition', label: 'Additions' },
            { id: 'deletion', label: 'Deletions' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setFilterType(item.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                filterType === item.id
                  ? 'bg-teal-500 text-navy-950 shadow-md shadow-teal-500/20'
                  : 'bg-navy-900 border border-navy-700/80 text-slate-300 hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Search & Actions */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 sm:w-60">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search diff summaries..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-navy-900 border border-navy-700 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-teal-400 transition-colors"
            />
          </div>

          {unreadCount > 0 && (
            <button
              onClick={onMarkAllAsRead}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-teal-500/40 bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 text-xs font-semibold transition-colors whitespace-nowrap"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark All Read
            </button>
          )}
        </div>
      </div>

      {/* Changes Timeline List */}
      {filteredChanges.length > 0 ? (
        <div className="space-y-4">
          {filteredChanges.map((change) => {
            const isExpanded = !!expandedIds[change.id];
            return (
              <div
                key={change.id}
                className={`rounded-xl border transition-all shadow-lg shadow-black/15 overflow-hidden ${
                  change.is_read
                    ? 'bg-navy-900/70 border-navy-800'
                    : 'bg-navy-900 border-teal-500/40 shadow-teal-950/20'
                }`}
              >
                {/* Header row */}
                <div className="p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-navy-900/90">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-base font-bold text-white">
                        {change.website_name}
                      </span>
                      <Badge
                        variant={
                          change.change_type === 'addition'
                            ? 'emerald'
                            : change.change_type === 'modification'
                            ? 'teal'
                            : 'rose'
                        }
                        size="sm"
                      >
                        {change.change_type}
                      </Badge>
                      {!change.is_read && (
                        <Badge variant="amber" size="sm" dot>
                          New Unread
                        </Badge>
                      )}
                    </div>

                    <p className="text-sm text-slate-300 font-medium">
                      {change.summary}
                    </p>

                    <div className="flex items-center gap-3 text-xs text-slate-400 pt-1">
                      <span className="flex items-center gap-1 font-mono">
                        <Calendar className="w-3 h-3 text-slate-500" />
                        {change.detected_at}
                      </span>
                      <span>•</span>
                      <span className="text-emerald-400 font-mono font-bold">
                        +{change.additions_count} lines
                      </span>
                      <span className="text-rose-400 font-mono font-bold">
                        -{change.deletions_count} lines
                      </span>
                    </div>
                  </div>

                  {/* Actions & Expand Toggle */}
                  <div className="flex items-center gap-2 self-end md:self-center">
                    {!change.is_read && (
                      <button
                        onClick={() => onMarkAsRead(change.id)}
                        className="px-2.5 py-1.5 rounded-lg border border-navy-700 hover:border-teal-500/40 bg-navy-800 text-slate-300 hover:text-white text-xs font-medium transition-colors"
                      >
                        Mark Read
                      </button>
                    )}

                    <button
                      onClick={() => toggleExpand(change.id)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-navy-800 hover:bg-navy-750 text-teal-300 text-xs font-semibold border border-navy-700 transition-colors"
                    >
                      <span>{isExpanded ? 'Collapse Diff' : 'View Diff'}</span>
                      {isExpanded ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Diff Body Component */}
                {isExpanded && (
                  <div className="p-4 sm:p-5 border-t border-navy-800 bg-navy-950/60">
                    <DiffViewer
                      oldText={change.old_content_snippet}
                      newText={change.new_content_snippet}
                      websiteName={change.website_name}
                      detectedAt={change.detected_at}
                      additionsCount={change.additions_count}
                      deletionsCount={change.deletions_count}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={History}
          title="No Change Records Found"
          description={
            searchQuery || filterType !== 'all'
              ? 'No detected webpage diffs match your filter criteria.'
              : 'When watched webpages change, Python difflib captures the delta and logs it here.'
          }
        />
      )}
    </div>
  );
};
