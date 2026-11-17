import React from 'react';
import { cn } from '../../lib/utils';

export interface StatusBadgeProps {
  status: 'online' | 'offline' | 'degraded' | 'critical' | 'high' | 'medium' | 'low' | 'normal';
  label?: string;
  pulse?: boolean;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  label,
  pulse = false,
  className,
}) => {
  const displayLabel = label || status.toUpperCase();

  const getStyles = () => {
    switch (status) {
      case 'online':
        return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'offline':
        return 'bg-gray-700/20 text-gray-400 border-gray-600/30';
      case 'degraded':
      case 'medium':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'critical':
        return 'bg-red-500/15 text-red-400 border-red-500/40 glow-red';
      case 'high':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'low':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'normal':
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getDotStyles = () => {
    switch (status) {
      case 'online':
        return 'bg-green-400';
      case 'offline':
        return 'bg-gray-500';
      case 'degraded':
      case 'medium':
        return 'bg-amber-400';
      case 'critical':
        return 'bg-red-400';
      case 'high':
        return 'bg-amber-400';
      case 'low':
        return 'bg-blue-400';
      case 'normal':
      default:
        return 'bg-slate-400';
    }
  };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono border font-medium uppercase tracking-wider',
        getStyles(),
        className
      )}
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full',
          getDotStyles(),
          pulse && status === 'online' && 'pulse-online',
          pulse && (status === 'critical' || status === 'offline') && 'pulse-offline',
          pulse && (status === 'degraded' || status === 'high') && 'pulse-warn'
        )}
      />
      {displayLabel}
    </span>
  );
};
