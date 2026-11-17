import React from 'react';
import { Search, RotateCcw } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface FilterOption {
  label: string;
  value: string;
}

export interface FilterBarProps {
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  searchPlaceholder?: string;
  filters?: {
    name: string;
    label: string;
    value: string;
    options: FilterOption[];
    onChange: (value: string) => void;
  }[];
  onReset?: () => void;
  children?: React.ReactNode;
  className?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchQuery = '',
  onSearchChange,
  searchPlaceholder = 'Search hosts, IPs, protocols...',
  filters = [],
  onReset,
  children,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-3 p-3 bg-[#0f1629] border border-[#1e3a5f] rounded-lg text-sm',
        className
      )}
    >
      {onSearchChange && (
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-3 py-1.5 bg-[#0a0e1a] border border-[#1e3a5f] rounded text-slate-200 text-xs font-mono placeholder-[#64748b] focus:outline-none focus:border-[#3b82f6]"
          />
        </div>
      )}

      {filters.map((filter) => (
        <div key={filter.name} className="flex items-center gap-1.5">
          <label className="text-xs text-[#94a3b8] font-mono">{filter.label}:</label>
          <select
            value={filter.value}
            onChange={(e) => filter.onChange(e.target.value)}
            className="bg-[#0a0e1a] border border-[#1e3a5f] rounded px-2 py-1.5 text-xs font-mono text-slate-200 focus:outline-none focus:border-[#3b82f6]"
          >
            {filter.options.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-[#0f1629]">
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      ))}

      {children}

      {onReset && (
        <button
          onClick={onReset}
          className="flex items-center gap-1 text-xs text-[#94a3b8] hover:text-white px-2 py-1.5 rounded hover:bg-[#1e3a5f]/40 transition-colors"
          title="Reset Filters"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Reset</span>
        </button>
      )}
    </div>
  );
};
