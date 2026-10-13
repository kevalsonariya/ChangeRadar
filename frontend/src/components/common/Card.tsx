import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  variant?: 'default' | 'glow' | 'subtle';
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  action,
  variant = 'default',
}) => {
  const variantStyles = {
    default: 'bg-navy-900/80 border-navy-700/60 shadow-lg shadow-black/20',
    glow: 'bg-navy-900/90 border-teal-500/30 shadow-lg shadow-teal-950/40 relative overflow-hidden',
    subtle: 'bg-navy-900/40 border-navy-800/80',
  };

  return (
    <div
      className={`rounded-xl border backdrop-blur-sm transition-all duration-200 ${variantStyles[variant]} ${className}`}
    >
      {(title || subtitle || action) && (
        <div className="flex items-center justify-between border-b border-navy-800/80 px-5 py-4">
          <div>
            {title && (
              <h3 className="text-base font-semibold tracking-tight text-white flex items-center gap-2">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="mt-0.5 text-xs text-slate-400 font-normal">
                {subtitle}
              </p>
            )}
          </div>
          {action && <div className="flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
};
