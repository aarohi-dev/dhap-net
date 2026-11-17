import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  RotateCcw,
  Clock,
  AlertTriangle,
  Radio,
} from 'lucide-react';
import { isDemoMode } from '../../lib/utils';
import { demoSystemStatus } from '../../data/fixtures';

export const TopBar: React.FC = () => {
  const location = useLocation();
  const [time, setTime] = useState(new Date().toUTCString());
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toUTCString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const getBreadcrumb = () => {
    const path = location.pathname.replace('/', '');
    if (!path) return 'Overview';
    return path
      .split('-')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  const handleRefresh = () => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
    }, 600);
  };

  const demoActive = isDemoMode() || demoSystemStatus.demo_mode;

  return (
    <header className="h-16 bg-[#0f1629] border-b border-[#1e3a5f] px-6 flex items-center justify-between z-20 shrink-0">
      {/* Left: Breadcrumbs */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="text-[#64748b]">DHAP-NET</span>
          <span className="text-[#1e3a5f]">/</span>
          <span className="text-white font-medium">{getBreadcrumb()}</span>
        </div>

        {/* Demo Mode Banner Indicator */}
        {demoActive && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border demo-banner animate-pulse">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            <span className="font-semibold text-amber-400">DEMO MODE ACTIVE</span>
            <span className="text-[#94a3b8] text-[10px] hidden sm:inline">
              — Offline pre-computed LANL dataset
            </span>
          </div>
        )}
      </div>

      {/* Right: Health, Refresh, Clock */}
      <div className="flex items-center gap-4 text-xs font-mono">
        {/* System Health */}
        <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded bg-[#0a0e1a] border border-[#1e3a5f]">
          <Radio className="w-3.5 h-3.5 text-red-400" />
          <span className="text-[#94a3b8]">Cluster:</span>
          <span className="text-red-400 font-semibold uppercase">Offline</span>
        </div>

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          className="p-1.5 rounded text-[#94a3b8] hover:text-white hover:bg-[#1e3a5f]/40 border border-[#1e3a5f] bg-[#0a0e1a] transition-colors"
          title="Refresh Data"
        >
          <RotateCcw
            className={`w-4 h-4 ${refreshing ? 'animate-spin text-blue-400' : ''}`}
          />
        </button>

        {/* Live Clock */}
        <div className="hidden lg:flex items-center gap-1.5 text-[#94a3b8] bg-[#0a0e1a] border border-[#1e3a5f] px-2.5 py-1 rounded">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-[11px]">{time}</span>
        </div>
      </div>
    </header>
  );
};
export default TopBar;
