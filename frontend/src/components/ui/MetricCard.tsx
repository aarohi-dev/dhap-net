import React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface MetricCardProps {
  title: string;
  value: string | number;
  subValue?: string;
  icon?: LucideIcon;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  variant?: 'default' | 'cyan' | 'red' | 'amber' | 'green';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subValue,
  icon: Icon,
  trend,
  variant = 'default',
  className,
}) => {
  const variantStyles = {
    default: 'border-[#1e3a5f] bg-[#0f1629] text-white',
    cyan: 'border-cyan-500/30 bg-[#0f1629] text-cyan-400 glow-cyan',
    red: 'border-red-500/30 bg-[#0f1629] text-red-400 glow-red',
    amber: 'border-amber-500/30 bg-[#0f1629] text-amber-400 glow-amber',
    green: 'border-green-500/30 bg-[#0f1629] text-green-400 glow-green',
  };

  return (
    <div
      className={cn(
        'card card-hover p-4 relative overflow-hidden transition-all duration-200',
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-center justify-between text-[#94a3b8] text-xs font-medium uppercase tracking-wider mb-2">
        <span>{title}</span>
        {Icon && <Icon className="w-4 h-4 opacity-75" />}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono tracking-tight text-white metric-num">
          {value}
        </span>
        {subValue && (
          <span className="text-xs text-[#94a3b8] font-mono">{subValue}</span>
        )}
      </div>
      {trend && (
        <div className="mt-2 text-xs flex items-center gap-1 font-mono">
          <span
            className={
              trend.isPositive ? 'text-green-400' : 'text-red-400'
            }
          >
            {trend.value}
          </span>
          <span className="text-[#64748b]">vs baseline</span>
        </div>
      )}
    </div>
  );
};
