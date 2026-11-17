import type { RiskLevel } from '../types';

/** Merge class names, filtering out falsy values */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}

/** Format a unix timestamp (seconds) to a readable string */
export function formatTime(epochSec: number): string {
  return new Date(epochSec * 1000).toLocaleString();
}

/** Format a unix timestamp to ISO string */
export function formatTimeISO(epochSec: number): string {
  return new Date(epochSec * 1000).toISOString();
}

/** Format bytes to human-readable */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/** Map probability to risk level */
export function getRiskLevel(prob: number): RiskLevel {
  if (prob >= 0.8) return 'critical';
  if (prob >= 0.6) return 'high';
  if (prob >= 0.4) return 'medium';
  if (prob >= 0.1) return 'low';
  return 'none';
}

/** Map risk level to Tailwind text color class */
export function getRiskColor(level: RiskLevel): string {
  switch (level) {
    case 'critical': return 'text-red-400';
    case 'high':     return 'text-amber-400';
    case 'medium':   return 'text-yellow-300';
    case 'low':      return 'text-blue-400';
    default:         return 'text-gray-400';
  }
}

/** Map risk level to Tailwind background color class */
export function getRiskBg(level: RiskLevel): string {
  switch (level) {
    case 'critical': return 'bg-red-500/15 border-red-500/30';
    case 'high':     return 'bg-amber-500/15 border-amber-500/30';
    case 'medium':   return 'bg-yellow-400/10 border-yellow-400/30';
    case 'low':      return 'bg-blue-500/10 border-blue-500/30';
    default:         return 'bg-gray-700/20 border-gray-600/30';
  }
}

/** Map protocol number to name */
export function protocolName(proto: number): string {
  switch (proto) {
    case 1:  return 'ICMP';
    case 6:  return 'TCP';
    case 17: return 'UDP';
    case 47: return 'GRE';
    case 50: return 'ESP';
    case 89: return 'OSPF';
    default: return `Proto/${proto}`;
  }
}

/** Format a probability as a percentage string */
export function formatProb(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`;
}

/** Clamp a number between min and max */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Truncate a string to maxLen characters with ellipsis */
export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + '…';
}

/** Format duration in seconds to human-readable */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

/** Check if the app is running in demo mode */
export function isDemoMode(): boolean {
  return import.meta.env.VITE_DEMO_MODE === 'true';
}
