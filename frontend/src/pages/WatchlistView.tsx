import React, { useState } from 'react';
import { 
  Globe, 
  Plus, 
  ExternalLink, 
  RefreshCw, 
  Trash2, 
  Clock, 
  Crosshair, 
  Search,
  Filter
} from 'lucide-react';
import type { MonitoredWebsite } from '../types';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

interface WatchlistViewProps {
  websites: MonitoredWebsite[];
  onOpenAddModal: () => void;
  onDeleteWebsite: (id: number) => void;
  onCheckWebsite: (id: number) => void;
  checkingId?: number | null;
}

export const WatchlistView: React.FC<WatchlistViewProps> = ({
  websites,
  onOpenAddModal,
  onDeleteWebsite,
  onCheckWebsite,
  checkingId,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [localSearch, setLocalSearch] = useState<string>('');

  const categories = ['All', 'University', 'Academics', 'Competitions', 'Financial Aid', 'Career'];

  const filteredWebsites = websites.filter((site) => {
    const matchesCategory = selectedCategory === 'All' || site.category === selectedCategory;
    const matchesSearch =
      site.name.toLowerCase().includes(localSearch.toLowerCase()) ||
      site.url.toLowerCase().includes(localSearch.toLowerCase()) ||
      site.category.toLowerCase().includes(localSearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Top Controls: Category Tabs, Search, Add Button */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          <Filter className="w-4 h-4 text-slate-500 mr-1 flex-shrink-0" />
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-teal-500 text-navy-950 shadow-md shadow-teal-500/20'
                  : 'bg-navy-900 border border-navy-700/80 text-slate-300 hover:text-white hover:border-slate-600'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Right Search & Add */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 md:w-56">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter watchlist..."
              value={localSearch}
              onChange={(e) => setLocalSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-navy-900 border border-navy-700 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-teal-400 transition-colors"
            />
          </div>

          <button
            onClick={onOpenAddModal}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold shadow-md shadow-teal-500/20 transition-colors whitespace-nowrap"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
            Add Target URL
          </button>
        </div>
      </div>

      {/* Grid of Monitored Websites */}
      {filteredWebsites.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredWebsites.map((site) => {
            const isChecking = checkingId === site.id;
            return (
              <div
                key={site.id}
                className="group rounded-xl bg-navy-900/90 border border-navy-700/80 hover:border-navy-600 p-5 flex flex-col justify-between transition-all shadow-lg shadow-black/15"
              >
                <div>
                  {/* Top Bar: Category & Status */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <Badge variant="indigo" size="sm">
                      {site.category}
                    </Badge>
                    <Badge
                      variant={
                        site.status === 'active'
                          ? 'emerald'
                          : site.status === 'warning'
                          ? 'amber'
                          : 'rose'
                      }
                      size="sm"
                      dot
                    >
                      {site.status === 'active' ? 'Active Polling' : site.status}
                    </Badge>
                  </div>

                  {/* Title & URL */}
                  <h4 className="text-base font-bold text-white mb-1.5 group-hover:text-teal-300 transition-colors">
                    {site.name}
                  </h4>
                  <a
                    href={site.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-teal-400 transition-colors truncate max-w-full font-mono mb-4"
                  >
                    <span className="truncate">{site.url}</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0" />
                  </a>

                  {/* Meta Attributes */}
                  <div className="space-y-2 p-3 rounded-lg bg-navy-950/70 border border-navy-800/80 text-xs">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        <Clock className="w-3.5 h-3.5 text-teal-400" />
                        Polling Interval:
                      </span>
                      <span className="font-semibold text-white">
                        Every {site.check_interval_minutes}m
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        <Crosshair className="w-3.5 h-3.5 text-teal-400" />
                        Target Scope:
                      </span>
                      <span className="font-mono text-[11px] text-teal-300 truncate max-w-[150px]">
                        {site.selector ? site.selector : 'Entire HTML body'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-300 pt-1 border-t border-navy-800">
                      <span className="text-slate-400">Last Checked:</span>
                      <span className="text-slate-300 font-mono text-[11px]">
                        {site.last_checked_at || 'Just now'}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-300">
                      <span className="text-slate-400">Total Diffs Recorded:</span>
                      <span className="px-1.5 py-0.2 rounded bg-teal-500/20 text-teal-300 font-mono font-bold text-[11px]">
                        {site.change_count} changes
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Actions */}
                <div className="mt-4 pt-3 border-t border-navy-800/80 flex items-center justify-between">
                  <button
                    onClick={() => onCheckWebsite(site.id)}
                    disabled={isChecking}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-navy-700 hover:border-teal-500/50 bg-navy-800/70 text-slate-200 hover:text-white text-xs font-semibold transition-colors disabled:opacity-60"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-teal-400 ${isChecking ? 'animate-spin' : ''}`} />
                    {isChecking ? 'Fetching...' : 'Check Now'}
                  </button>

                  <button
                    onClick={() => onDeleteWebsite(site.id)}
                    className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                    title="Remove from watchlist"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={Globe}
          title="No Monitored Websites Found"
          description={
            localSearch || selectedCategory !== 'All'
              ? 'No target websites match your search query or selected category filter.'
              : 'You have not added any webpage URLs to ChangeRadar yet. Add your first university portal or public notice board.'
          }
          actionText="Add Webpage Target"
          onAction={onOpenAddModal}
        />
      )}
    </div>
  );
};
