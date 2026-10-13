import React, { useState } from 'react';
import { 
  CalendarClock, 
  ExternalLink, 
  Plus, 
  Clock, 
  Search, 
  AlertTriangle 
} from 'lucide-react';
import type { DeadlineItem, DeadlinePriority } from '../types';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

interface DeadlinesViewProps {
  deadlines: DeadlineItem[];
  onAddDeadline: (deadline: Omit<DeadlineItem, 'id'>) => void;
}

export const DeadlinesView: React.FC<DeadlinesViewProps> = ({
  deadlines,
  onAddDeadline,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // New Deadline form state
  const [newTitle, setNewTitle] = useState('');
  const [newDate, setNewDate] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newCategory, setNewCategory] = useState('Academic');
  const [newPriority, setNewPriority] = useState<DeadlinePriority>('high');
  const [newDescription, setNewDescription] = useState('');

  const filteredDeadlines = deadlines.filter((d) => {
    let matchesStatus = true;
    if (filterStatus === 'urgent') {
      matchesStatus = d.days_left <= 3 || d.status === 'critical';
    } else if (filterStatus === 'upcoming') {
      matchesStatus = d.days_left > 3 && d.status !== 'passed';
    } else if (filterStatus === 'passed') {
      matchesStatus = d.status === 'passed';
    }

    const matchesSearch =
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.category.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  const handleCreateDeadline = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDate.trim()) return;

    onAddDeadline({
      title: newTitle.trim(),
      due_date: newDate.trim(),
      days_left: 7, // calculated default
      source_url: newUrl.trim() || 'https://www.example.edu',
      priority: newPriority,
      status: 'upcoming',
      category: newCategory,
      description: newDescription.trim() || undefined,
    });

    setNewTitle('');
    setNewDate('');
    setNewUrl('');
    setNewDescription('');
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Top Filter & Actions */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
          {[
            { id: 'all', label: 'All Deadlines' },
            { id: 'urgent', label: 'Urgent (≤ 3 Days)' },
            { id: 'upcoming', label: 'Upcoming' },
            { id: 'passed', label: 'Passed / Archived' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterStatus(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                filterStatus === tab.id
                  ? 'bg-teal-500 text-navy-950 shadow-md shadow-teal-500/20'
                  : 'bg-navy-900 border border-navy-700/80 text-slate-300 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <div className="relative flex-1 sm:w-56">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search deadlines..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-navy-900 border border-navy-700 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-teal-400 transition-colors"
            />
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold shadow-md shadow-teal-500/20 transition-colors whitespace-nowrap"
          >
            <Plus className="w-4 h-4 stroke-[2.5]" />
            Add Deadline
          </button>
        </div>
      </div>

      {/* Deadlines Card Grid */}
      {filteredDeadlines.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredDeadlines.map((item) => {
            const isUrgent = item.days_left <= 3 || item.status === 'critical';
            return (
              <div
                key={item.id}
                className={`rounded-xl border p-5 flex flex-col justify-between transition-all shadow-lg ${
                  isUrgent
                    ? 'bg-navy-900/95 border-rose-500/40 shadow-rose-950/20'
                    : 'bg-navy-900/90 border-navy-700/80 hover:border-navy-600 shadow-black/20'
                }`}
              >
                <div>
                  {/* Category & Urgency countdown badge */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <Badge variant="indigo" size="sm">
                      {item.category}
                    </Badge>
                    <Badge
                      variant={isUrgent ? 'rose' : item.days_left <= 7 ? 'amber' : 'teal'}
                      size="sm"
                      dot={isUrgent}
                    >
                      {item.days_left > 0 ? `${item.days_left} Days Left` : 'Due Today'}
                    </Badge>
                  </div>

                  {/* Title */}
                  <h4 className="text-base font-bold text-white mb-2 leading-snug">
                    {item.title}
                  </h4>

                  {/* Description if any */}
                  {item.description && (
                    <p className="text-xs text-slate-300 leading-relaxed mb-4">
                      {item.description}
                    </p>
                  )}

                  {/* Metadata pill */}
                  <div className="p-3 rounded-lg bg-navy-950/70 border border-navy-800 space-y-2 text-xs">
                    <div className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        <Clock className="w-3.5 h-3.5 text-teal-400" />
                        Cutoff Date:
                      </span>
                      <span className="font-semibold text-white font-mono">
                        {item.due_date}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-slate-300">
                      <span className="flex items-center gap-1.5 text-slate-400">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                        Priority:
                      </span>
                      <span
                        className={`font-semibold capitalize ${
                          item.priority === 'high'
                            ? 'text-rose-400'
                            : item.priority === 'medium'
                            ? 'text-amber-400'
                            : 'text-teal-400'
                        }`}
                      >
                        {item.priority} Priority
                      </span>
                    </div>
                  </div>
                </div>

                {/* Footer link to source webpage */}
                <div className="mt-4 pt-3 border-t border-navy-800 flex items-center justify-between text-xs">
                  <span className="text-slate-400">Verified from public portal</span>
                  <a
                    href={item.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-teal-400 hover:text-teal-300 font-medium"
                  >
                    Open Source
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={CalendarClock}
          title="No Deadlines in Radar"
          description={
            searchQuery || filterStatus !== 'all'
              ? 'No deadlines match your current search or status filter.'
              : 'Deadlines automatically extract from monitored circulars and exam schedules.'
          }
          actionText="Add Tracked Deadline"
          onAction={() => setIsModalOpen(true)}
        />
      )}

      {/* Add Deadline Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-navy-900 border border-navy-700 shadow-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <CalendarClock className="w-5 h-5 text-teal-400" />
              Add Tracked Deadline
            </h3>
            <form onSubmit={handleCreateDeadline} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. GTU Winter Exam Fee Submission"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Due Date *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Oct 25, 2026"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Category
                  </label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                  >
                    <option value="Academic">Academic</option>
                    <option value="Exams">Exams</option>
                    <option value="Competitions">Competitions</option>
                    <option value="Scholarships">Scholarships</option>
                    <option value="Internships">Internships</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Priority
                  </label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as DeadlinePriority)}
                    className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                  >
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Source Webpage URL
                </label>
                <input
                  type="url"
                  placeholder="https://..."
                  value={newUrl}
                  onChange={(e) => setNewUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Description / Instructions
                </label>
                <textarea
                  rows={2}
                  placeholder="Additional instructions or prerequisite steps"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-navy-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-navy-700 text-slate-300 text-xs font-medium hover:bg-navy-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold"
                >
                  Save Deadline
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
