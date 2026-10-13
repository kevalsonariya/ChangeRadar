import React, { useState } from 'react';
import { 
  Server, 
  Check, 
  RefreshCw, 
  Database,
  Radio,
  Sliders,
  ShieldCheck
} from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

interface SettingsViewProps {
  isBackendConnected: boolean;
  isDemoMode: boolean;
  onToggleDemoMode: (val: boolean) => void;
  onTestBackendConnection: () => Promise<void>;
  isTestingConnection: boolean;
  backendError?: string | null;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  isBackendConnected,
  isDemoMode,
  onToggleDemoMode,
  onTestBackendConnection,
  isTestingConnection,
  backendError,
}) => {
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');
  const [userAgent, setUserAgent] = useState('ChangeRadar/0.1 (Webpage Content Monitor; College SGP)');
  const [defaultInterval, setDefaultInterval] = useState('60');
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Backend Integration & Mode Card */}
      <Card
        title="Backend Service Integration"
        subtitle="Manage communication with the Python FastAPI backend engine"
      >
        <div className="space-y-5">
          {/* Status Indicator Bar */}
          <div className="p-4 rounded-xl bg-navy-950/70 border border-navy-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div
                className={`p-2.5 rounded-lg border ${
                  isBackendConnected
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                }`}
              >
                <Server className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-white">
                    {isBackendConnected ? 'FastAPI Service Connected' : 'FastAPI Service Standby'}
                  </h4>
                  <Badge
                    variant={isBackendConnected ? 'emerald' : 'amber'}
                    size="sm"
                    dot
                  >
                    {isBackendConnected ? 'Live Connection' : 'Offline / Standby'}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  {isBackendConnected
                    ? 'Successfully communicating with http://localhost:8000/health'
                    : 'Backend service is not running. The dashboard gracefully displays demo data.'}
                </p>
              </div>
            </div>

            <button
              onClick={onTestBackendConnection}
              disabled={isTestingConnection}
              className="px-3.5 py-2 rounded-lg border border-navy-700 hover:border-teal-500/40 bg-navy-800 text-teal-300 text-xs font-semibold flex items-center gap-1.5 transition-colors self-start sm:self-auto disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isTestingConnection ? 'animate-spin' : ''}`} />
              {isTestingConnection ? 'Testing...' : 'Test Connection'}
            </button>
          </div>

          {backendError && (
            <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/30 text-xs text-rose-300">
              <span className="font-semibold">Connection Notice:</span> {backendError}
            </div>
          )}

          {/* Demo Mode Toggle */}
          <div className="flex items-center justify-between p-4 rounded-xl bg-navy-950/40 border border-navy-800">
            <div>
              <div className="text-sm font-semibold text-white flex items-center gap-2">
                <Radio className="w-4 h-4 text-teal-400" />
                Demonstration Mode (Visual Mock Data)
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Displays realistic demonstration targets and diffs when backend is offline
              </p>
            </div>

            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={isDemoMode}
                onChange={(e) => onToggleDemoMode(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-navy-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-teal-500"></div>
            </label>
          </div>
        </div>
      </Card>

      {/* Scraper Engine Configurations */}
      <Card
        title="Scraper & Diffing Engine Settings"
        subtitle="Configure HTTPX headers, default check intervals, and difflib parameters"
      >
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Backend API Base URL
            </label>
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrl(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs font-mono outline-none focus:border-teal-400"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              HTTP Request User-Agent Header
            </label>
            <input
              type="text"
              value={userAgent}
              onChange={(e) => setUserAgent(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs font-mono outline-none focus:border-teal-400"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Default Polling Interval (Minutes)
              </label>
              <select
                value={defaultInterval}
                onChange={(e) => setDefaultInterval(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-700 text-white text-xs outline-none focus:border-teal-400"
              >
                <option value="15">15 Minutes</option>
                <option value="30">30 Minutes</option>
                <option value="60">60 Minutes (Default)</option>
                <option value="120">2 Hours</option>
                <option value="360">6 Hours</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Database Engine
              </label>
              <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg bg-navy-950 border border-navy-800 text-xs text-slate-300">
                <Database className="w-4 h-4 text-teal-400" />
                <span>SQLite (changeradar.db)</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-navy-800">
            {savedSuccess ? (
              <span className="text-xs text-teal-300 flex items-center gap-1 font-semibold">
                <Check className="w-4 h-4" /> Preferences saved!
              </span>
            ) : <span />}

            <button
              type="submit"
              className="px-5 py-2 rounded-lg bg-teal-500 hover:bg-teal-400 text-navy-950 text-xs font-semibold shadow-md shadow-teal-500/20 transition-colors"
            >
              Save Engine Settings
            </button>
          </div>
        </form>
      </Card>

      {/* College Project Meta Card */}
      <Card
        title="Project Architecture & Specifications"
        subtitle="College 5th Semester SGP (Software Group Project) MVP Specification"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-slate-300">
          <div className="p-3 rounded-lg bg-navy-950/60 border border-navy-800 space-y-1.5">
            <div className="font-semibold text-white flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-teal-400" />
              Frontend Stack
            </div>
            <p className="text-slate-400 leading-relaxed">
              React 19 + TypeScript + Vite + Tailwind CSS with dark navy & teal design system and Lucide icons.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-navy-950/60 border border-navy-800 space-y-1.5">
            <div className="font-semibold text-white flex items-center gap-1.5">
              <Sliders className="w-4 h-4 text-teal-400" />
              Backend Stack
            </div>
            <p className="text-slate-400 leading-relaxed">
              Python FastAPI + SQLite database + HTTPX async fetcher + BeautifulSoup HTML parser + difflib delta engine.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};
