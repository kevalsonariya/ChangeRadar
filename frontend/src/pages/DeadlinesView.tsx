import React, { useState } from 'react';
import { 
  CalendarClock, 
  ExternalLink, 
  Plus, 
  Clock, 
  Search, 
  AlertTriangle,
  RotateCcw,
  Trash2,
  Pencil,
  Check
} from 'lucide-react';
import type { DeadlineItem, DeadlinePriority } from '../types';
import { Badge } from '../components/common/Badge';
import { EmptyState } from '../components/common/EmptyState';

interface DeadlinesViewProps {
  deadlines: DeadlineItem[];
  onAddDeadline: (deadline: {
    title: string;
    due_date: string;
    priority?: DeadlinePriority;
    category?: string;
    description?: string;
    source_url?: string;
  }) => Promise<{ success: boolean; error?: string }>;
  onToggleComplete?: (id: number) => Promise<void>;
  onDeleteDeadline?: (id: number) => Promise<void>;
  onEditDeadline?: (id: number, data: Partial<DeadlineItem>) => Promise<{ success: boolean; error?: string }>;
}

export const DeadlinesView: React.FC<DeadlinesViewProps> = ({
  deadlines,
  onAddDeadline,
  onToggleComplete,
  onDeleteDeadline,
  onEditDeadline,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Add Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isSubmittingAdd, setIsSubmittingAdd] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [newTitle, setNewTitle] = useState('');
  const [newDate, setNewDate] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newCategory, setNewCategory] = useState('Academic');
  const [newPriority, setNewPriority] = useState<DeadlinePriority>('high');
  const [newDescription, setNewDescription] = useState('');

  // Edit Modal State
  const [editingItem, setEditingItem] = useState<DeadlineItem | null>(null);
  const [isSubmittingEdit, setIsSubmittingEdit] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  const [editTitle, setEditTitle] = useState('');
  const [editDate, setEditDate] = useState('');
  const [editUrl, setEditUrl] = useState('');
  const [editCategory, setEditCategory] = useState('Academic');
  const [editPriority, setEditPriority] = useState<DeadlinePriority>('medium');
  const [editDescription, setEditDescription] = useState('');

  const filteredDeadlines = deadlines.filter((d) => {
    let matchesStatus = true;
    if (filterStatus === 'urgent') {
      matchesStatus = !d.is_completed && (d.days_left <= 3 || d.status === 'critical');
    } else if (filterStatus === 'upcoming') {
      matchesStatus = !d.is_completed && d.days_left > 3 && d.status !== 'passed';
    } else if (filterStatus === 'passed') {
      matchesStatus = d.status === 'passed' && !d.is_completed;
    } else if (filterStatus === 'completed') {
      matchesStatus = !!d.is_completed;
    }

    const matchesSearch =
      d.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.category.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesStatus && matchesSearch;
  });

  const handleOpenAddModal = () => {
    setNewTitle('');
    setNewDate('');
    setNewUrl('');
    setNewDescription('');
    setNewPriority('high');
    setNewCategory('Academic');
    setAddError(null);
    setIsAddModalOpen(true);
  };

  const handleCreateDeadline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDate.trim()) return;

    setIsSubmittingAdd(true);
    setAddError(null);

    const res = await onAddDeadline({
      title: newTitle.trim(),
      due_date: newDate.trim(),
      source_url: newUrl.trim() || undefined,
      priority: newPriority,
      category: newCategory,
      description: newDescription.trim() || undefined,
    });

    setIsSubmittingAdd(false);
    if (res.success) {
      setIsAddModalOpen(false);
    } else {
      setAddError(res.error || 'Failed to create deadline. Please verify date format.');
    }
  };

  const handleOpenEditModal = (item: DeadlineItem) => {
    setEditingItem(item);
    setEditTitle(item.title);
    setEditDate(item.due_date);
    setEditUrl(item.source_url || '');
    setEditCategory(item.category || 'Academic');
    setEditPriority(item.priority || 'medium');
    setEditDescription(item.description || '');
    setEditError(null);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem || !onEditDeadline) return;
    if (!editTitle.trim() || !editDate.trim()) return;

    setIsSubmittingEdit(true);
    setEditError(null);

    const res = await onEditDeadline(editingItem.id, {
      title: editTitle.trim(),
      due_date: editDate.trim(),
      source_url: editUrl.trim() || undefined,
      priority: editPriority,
      category: editCategory,
      description: editDescription.trim() || undefined,
    });

    setIsSubmittingEdit(false);
    if (res.success) {
      setEditingItem(null);
    } else {
      setEditError(res.error || 'Failed to update deadline.');
    }
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
            { id: 'passed', label: 'Passed / Expired' },
            { id: 'completed', label: 'Completed' },
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
            onClick={handleOpenAddModal}
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
            const isCompleted = !!item.is_completed;
            const isUrgent = !isCompleted && (item.days_left <= 3 || item.status === 'critical');
            return (
              <div
                key={item.id}
                className={`rounded-xl border p-5 flex flex-col justify-between transition-all shadow-lg ${
                  isCompleted
                    ? 'bg-navy-900/50 border-navy-800 opacity-80'
                    : isUrgent
                    ? 'bg-navy-900/95 border-rose-500/40 shadow-rose-950/20'
                    : 'bg-navy-900/90 border-navy-700/80 hover:border-navy-600 shadow-black/20'
                }`}
              >
                <div>
                  {/* Category & Status countdown badge */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <Badge variant="indigo" size="sm">
                      {item.category}
                    </Badge>
                    {isCompleted ? (
                      <Badge variant="teal" size="sm">
                        ✓ Completed
                      </Badge>
                    ) : (
                      <Badge
                        variant={isUrgent ? 'rose' : item.days_left <= 7 ? 'amber' : 'teal'}
                        size="sm"
                        dot={isUrgent}
                      >
                        {item.days_left > 0 ? `${item.days_left} Days Left` : 'Due Today'}
                      </Badge>
                    )}
                  </div>

                  {/* Title */}
                  <h4
                    className={`text-base font-bold mb-2 leading-snug ${
                      isCompleted ? 'text-slate-400 line-through' : 'text-white'
                    }`}
                  >
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
                        Due Date:
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

                {/* Footer with actions */}
                <div className="mt-4 pt-3 border-t border-navy-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    {onToggleComplete && (
                      <button
                        onClick={() => onToggleComplete(item.id)}
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                          isCompleted
                            ? 'bg-navy-800 border border-navy-700 text-slate-300 hover:text-white'
                            : 'bg-teal-500/10 border border-teal-500/30 text-teal-300 hover:bg-teal-500/20'
                        }`}
                        title={isCompleted ? 'Reopen deadline' : 'Mark deadline as completed'}
                      >
                        {isCompleted ? (
                          <>
                            <RotateCcw className="w-3 h-3" />
                            Reopen
                          </>
                        ) : (
                          <>
                            <Check className="w-3 h-3" />
                            Complete
                          </>
                        )}
                      </button>
                    )}

                    {onEditDeadline && (
                      <button
                        onClick={() => handleOpenEditModal(item)}
                        className="p-1 rounded-md text-slate-400 hover:text-teal-400 hover:bg-navy-800 transition-colors"
                        title="Edit deadline"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    )}

                    {onDeleteDeadline && (
                      <button
                        onClick={() => onDeleteDeadline(item.id)}
                        className="p-1 rounded-md text-slate-400 hover:text-rose-400 hover:bg-navy-800 transition-colors"
                        title="Delete deadline"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>

                  {item.source_url ? (
                    <a
                      href={item.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-teal-400 hover:text-teal-300 font-medium"
                    >
                      Source
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-slate-400 text-[11px]">Manual Tracker</span>
                  )}
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
          onAction={handleOpenAddModal}
        />
      )}

      {/* Add Deadline Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl bg-navy-900 border border-navy-700 shadow-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <CalendarClock className="w-5 h-5 text-teal-400" />
              Add Tracked Deadline
            </h3>

            {addError && (
              <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-200 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                <span>{addError}</span>
              </div>
            )}

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
                  Due Date (YYYY-MM-DD or standard format) *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026-11-20 or Nov 20, 2026"
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
                  disabled={isSubmittingAdd}
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-3.5 py-1.5 rounded-lg border border-navy-700 text-slate-300 text-xs font-medium hover:bg-navy-800 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingAdd}
                  className="px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isSubmittingAdd ? 'Saving...' : 'Save Deadline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Deadline Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl bg-navy-900 border border-navy-700 shadow-2xl p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Pencil className="w-5 h-5 text-teal-400" />
              Edit Tracked Deadline
            </h3>

            {editError && (
              <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-500/50 text-rose-200 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                <span>{editError}</span>
              </div>
            )}

            <form onSubmit={handleSaveEdit} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  required
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
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
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Category
                  </label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
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
                    value={editPriority}
                    onChange={(e) => setEditPriority(e.target.value as DeadlinePriority)}
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
                  value={editUrl}
                  onChange={(e) => setEditUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Description / Instructions
                </label>
                <textarea
                  rows={2}
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-navy-800">
                <button
                  type="button"
                  disabled={isSubmittingEdit}
                  onClick={() => setEditingItem(null)}
                  className="px-3.5 py-1.5 rounded-lg border border-navy-700 text-slate-300 text-xs font-medium hover:bg-navy-800 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingEdit}
                  className="px-4 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold disabled:opacity-50 flex items-center gap-1.5"
                >
                  {isSubmittingEdit ? 'Saving...' : 'Update Deadline'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
