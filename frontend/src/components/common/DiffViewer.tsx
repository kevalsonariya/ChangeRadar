import React, { useState } from 'react';
import { Columns, AlignLeft, Check, Copy } from 'lucide-react';

interface DiffViewerProps {
  oldText?: string;
  newText?: string;
  websiteName?: string;
  detectedAt?: string;
  additionsCount?: number;
  deletionsCount?: number;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  oldText = '',
  newText = '',
  websiteName,
  detectedAt,
  additionsCount = 0,
  deletionsCount = 0,
}) => {
  const [mode, setMode] = useState<'split' | 'unified'>('split');
  const [copied, setCopied] = useState(false);

  const handleCopyNew = () => {
    navigator.clipboard.writeText(newText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const oldLines = oldText ? oldText.split('\n') : [];
  const newLines = newText ? newText.split('\n') : [];

  return (
    <div className="rounded-xl border border-navy-700/80 bg-navy-900/90 overflow-hidden text-xs">
      {/* Diff Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-navy-950/80 border-b border-navy-800">
        <div className="flex items-center gap-3">
          {websiteName && (
            <span className="font-semibold text-white text-sm">{websiteName}</span>
          )}
          {detectedAt && (
            <span className="text-slate-400 text-xs">Detected: {detectedAt}</span>
          )}
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-500/30 font-mono font-bold">
              +{additionsCount}
            </span>
            <span className="px-2 py-0.5 rounded bg-rose-950/60 text-rose-400 border border-rose-500/30 font-mono font-bold">
              -{deletionsCount}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-navy-700 p-0.5 bg-navy-900">
            <button
              onClick={() => setMode('split')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                mode === 'split'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Columns className="w-3.5 h-3.5" />
              Side-by-Side
            </button>
            <button
              onClick={() => setMode('unified')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                mode === 'unified'
                  ? 'bg-teal-500/20 text-teal-300 border border-teal-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlignLeft className="w-3.5 h-3.5" />
              Unified
            </button>
          </div>

          <button
            onClick={handleCopyNew}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-navy-700 hover:border-slate-600 bg-navy-800 text-slate-300 hover:text-white transition-colors"
            title="Copy new version text"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-teal-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Copied' : 'Copy New'}
          </button>
        </div>
      </div>

      {/* Diff Content View */}
      {mode === 'split' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-navy-800 font-mono text-[13px] leading-relaxed">
          {/* Previous / Old text */}
          <div className="p-3 bg-navy-950/40">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-rose-400/80 mb-2 px-1 flex items-center justify-between">
              <span>Previous Version</span>
              <span className="text-slate-500">Deleted / Modified</span>
            </div>
            <div className="space-y-1">
              {oldLines.length > 0 ? (
                oldLines.map((line, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 px-2 py-0.5 rounded bg-rose-950/20 text-rose-200 border-l-2 border-rose-500/60"
                  >
                    <span className="select-none text-rose-400/50 w-5 text-right text-xs">
                      {idx + 1}
                    </span>
                    <span className="select-none text-rose-400">-</span>
                    <span className="break-all whitespace-pre-wrap">{line}</span>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic p-2">No previous content</div>
              )}
            </div>
          </div>

          {/* Current / New text */}
          <div className="p-3 bg-navy-950/20">
            <div className="text-[11px] uppercase tracking-wider font-semibold text-teal-400 mb-2 px-1 flex items-center justify-between">
              <span>Detected Change (Current)</span>
              <span className="text-teal-400/80">Added / New Content</span>
            </div>
            <div className="space-y-1">
              {newLines.length > 0 ? (
                newLines.map((line, idx) => (
                  <div
                    key={idx}
                    className="flex items-start gap-2 px-2 py-0.5 rounded bg-teal-950/30 text-teal-200 border-l-2 border-teal-400"
                  >
                    <span className="select-none text-teal-400/50 w-5 text-right text-xs">
                      {idx + 1}
                    </span>
                    <span className="select-none text-teal-400">+</span>
                    <span className="break-all whitespace-pre-wrap font-medium">{line}</span>
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic p-2">No new content</div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* Unified View */
        <div className="p-4 font-mono text-[13px] leading-relaxed space-y-1 bg-navy-950/50">
          <div className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 mb-2">
            Sequential Unified Inspection
          </div>
          {oldLines.map((line, idx) => (
            <div
              key={`old-${idx}`}
              className="flex items-start gap-2 px-2 py-0.5 rounded bg-rose-950/20 text-rose-200 border-l-2 border-rose-500/60"
            >
              <span className="select-none text-rose-400/50 w-6 text-right text-xs">
                -{idx + 1}
              </span>
              <span className="select-none text-rose-400">-</span>
              <span className="break-all whitespace-pre-wrap">{line}</span>
            </div>
          ))}
          {newLines.map((line, idx) => (
            <div
              key={`new-${idx}`}
              className="flex items-start gap-2 px-2 py-0.5 rounded bg-teal-950/30 text-teal-200 border-l-2 border-teal-400"
            >
              <span className="select-none text-teal-400/50 w-6 text-right text-xs">
                +{idx + 1}
              </span>
              <span className="select-none text-teal-400">+</span>
              <span className="break-all whitespace-pre-wrap font-medium">{line}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
