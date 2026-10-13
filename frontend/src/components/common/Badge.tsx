import React from 'react';

type BadgeVariant =
  | 'teal'
  | 'emerald'
  | 'amber'
  | 'rose'
  | 'sky'
  | 'indigo'
  | 'slate';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  dot?: boolean;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'teal',
  size = 'sm',
  dot = false,
  className = '',
}) => {
  const variantStyles: Record<BadgeVariant, { bg: string; text: string; border: string; dotColor: string }> = {
    teal: {
      bg: 'bg-teal-950/60',
      text: 'text-teal-300',
      border: 'border-teal-500/30',
      dotColor: 'bg-teal-400',
    },
    emerald: {
      bg: 'bg-emerald-950/60',
      text: 'text-emerald-300',
      border: 'border-emerald-500/30',
      dotColor: 'bg-emerald-400',
    },
    amber: {
      bg: 'bg-amber-950/60',
      text: 'text-amber-300',
      border: 'border-amber-500/30',
      dotColor: 'bg-amber-400',
    },
    rose: {
      bg: 'bg-rose-950/60',
      text: 'text-rose-300',
      border: 'border-rose-500/30',
      dotColor: 'bg-rose-400',
    },
    sky: {
      bg: 'bg-sky-950/60',
      text: 'text-sky-300',
      border: 'border-sky-500/30',
      dotColor: 'bg-sky-400',
    },
    indigo: {
      bg: 'bg-indigo-950/60',
      text: 'text-indigo-300',
      border: 'border-indigo-500/30',
      dotColor: 'bg-indigo-400',
    },
    slate: {
      bg: 'bg-slate-800/60',
      text: 'text-slate-300',
      border: 'border-slate-700/50',
      dotColor: 'bg-slate-400',
    },
  };

  const current = variantStyles[variant];
  const sizeStyles = size === 'sm' ? 'text-xs px-2.5 py-0.5' : 'text-sm px-3 py-1';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${current.bg} ${current.text} ${current.border} ${sizeStyles} ${className}`}
    >
      {dot && (
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${current.dotColor} animate-pulse`} />
      )}
      {children}
    </span>
  );
};
