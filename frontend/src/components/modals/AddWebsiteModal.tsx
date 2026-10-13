import React, { useState } from 'react';
import { X, Globe, Tag, Clock, Crosshair, Plus } from 'lucide-react';

interface AddWebsiteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (website: {
    name: string;
    url: string;
    category: string;
    selector?: string;
    check_interval_minutes: number;
  }) => void;
}

export const AddWebsiteModal: React.FC<AddWebsiteModalProps> = ({
  isOpen,
  onClose,
  onAdd,
}) => {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [category, setCategory] = useState('Academic');
  const [selector, setSelector] = useState('');
  const [checkInterval, setCheckInterval] = useState('60');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;

    onAdd({
      name: name.trim(),
      url: url.trim(),
      category: category.trim() || 'General',
      selector: selector.trim() || undefined,
      check_interval_minutes: parseInt(checkInterval, 10) || 60,
    });

    setName('');
    setUrl('');
    setSelector('');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/80 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl bg-navy-900 border border-navy-700 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-navy-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center border border-teal-500/30">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Add Website to Watchlist</h3>
              <p className="text-xs text-slate-400">Configure URL and frequency for continuous change detection</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-navy-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Friendly Display Name *
            </label>
            <input
              type="text"
              required
              placeholder="e.g. GTU Examination Circulars"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-white text-sm placeholder:text-slate-500 outline-none transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-teal-400" />
              Target Webpage URL *
            </label>
            <input
              type="url"
              required
              placeholder="https://www.example.edu/announcements"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-white text-sm placeholder:text-slate-500 outline-none transition-colors"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Tag className="w-3.5 h-3.5 text-teal-400" />
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-white text-sm outline-none transition-colors"
              >
                <option value="Academic">Academic</option>
                <option value="University">University</option>
                <option value="Exams">Exams</option>
                <option value="Competitions">Competitions</option>
                <option value="Financial Aid">Financial Aid</option>
                <option value="Career">Career</option>
                <option value="General">General</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-teal-400" />
                Poll Interval
              </label>
              <select
                value={checkInterval}
                onChange={(e) => setCheckInterval(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-white text-sm outline-none transition-colors"
              >
                <option value="15">Every 15 minutes</option>
                <option value="30">Every 30 minutes</option>
                <option value="60">Every 1 hour (Default)</option>
                <option value="120">Every 2 hours</option>
                <option value="360">Every 6 hours</option>
                <option value="1440">Once daily</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Crosshair className="w-3.5 h-3.5 text-teal-400" />
                CSS Target Selector (Optional)
              </span>
              <span className="text-[11px] text-slate-400 normal-case">Leave empty for whole page</span>
            </label>
            <input
              type="text"
              placeholder=".main-content or #circular-table"
              value={selector}
              onChange={(e) => setSelector(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 focus:border-teal-400 focus:ring-1 focus:ring-teal-400 text-white text-sm font-mono placeholder:text-slate-500 outline-none transition-colors"
            />
          </div>

          {/* Footer buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-navy-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-lg border border-navy-700 text-slate-300 hover:text-white hover:bg-navy-800 text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-sm font-semibold transition-colors shadow-md shadow-teal-500/20 active:scale-98"
            >
              Start Monitoring
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
