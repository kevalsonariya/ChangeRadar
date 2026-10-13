import React from 'react';

interface LoadingSpinnerProps {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  label = 'Loading data...',
  size = 'md',
}) => {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-2',
    lg: 'w-12 h-12 border-3',
  };

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div
        className={`${sizeMap[size]} border-teal-500/20 border-t-teal-400 rounded-full animate-spin`}
      />
      {label && (
        <p className="mt-3 text-xs tracking-wide uppercase text-slate-400 font-medium">
          {label}
        </p>
      )}
    </div>
  );
};
