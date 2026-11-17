import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Inbox } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center border border-[#1e3a5f] rounded-lg bg-[#0f1629]/50',
        className
      )}
    >
      <div className="w-12 h-12 rounded-full bg-[#1e3a5f]/30 flex items-center justify-center text-[#94a3b8] mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200 mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-[#64748b] max-w-sm mb-4 font-mono">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-3 py-1.5 rounded text-xs font-mono font-medium bg-[#3b82f6] text-white hover:bg-blue-600 transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};
