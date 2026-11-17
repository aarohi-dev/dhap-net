import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  Radio,
  Share2,
  TrendingUp,
  AlertTriangle,
  Search,
  BarChart3,
  FileText,
  ChevronLeft,
  ChevronRight,
  Shield,
  Layers,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { demoSystemStatus } from '../../data/fixtures';

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { name: 'Overview', path: '/overview', icon: Activity },
  { name: 'Live Monitoring', path: '/monitoring', icon: Radio },
  { name: 'Attack Graph', path: '/graph', icon: Share2 },
  { name: 'Predictions', path: '/predictions', icon: TrendingUp },
  { name: 'Anomalies', path: '/anomalies', icon: AlertTriangle },
  { name: 'Entity Investigation', path: '/entities', icon: Search },
  { name: 'Analytics', path: '/analytics', icon: BarChart3 },
  { name: 'Reports', path: '/reports', icon: FileText },
];

export const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        'h-screen bg-[#0a0e1a] border-r border-[#1e3a5f] flex flex-col transition-all duration-300 z-30 select-none shrink-0',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-[#1e3a5f]">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold font-mono tracking-wider text-sm text-white flex items-center gap-1.5">
                DHAP-NET
                <span className="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1 py-0.2 rounded font-normal">
                  v1.0
                </span>
              </div>
              <div className="text-[10px] text-[#64748b] font-mono tracking-tight">
                Cyber Defense Platform
              </div>
            </div>
          </div>
        )}

        {collapsed && (
          <div className="w-8 h-8 mx-auto rounded bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center text-white shadow-lg">
            <Shield className="w-5 h-5" />
          </div>
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'p-1.5 rounded text-[#94a3b8] hover:text-white hover:bg-[#1e3a5f]/40 transition-colors',
            collapsed && 'hidden'
          )}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {/* Nav List */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-mono transition-all group',
                  isActive
                    ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 font-semibold'
                    : 'text-[#94a3b8] hover:text-white hover:bg-[#0f1629] border border-transparent'
                )
              }
              title={collapsed ? item.name : undefined}
            >
              <Icon className="w-4 h-4 shrink-0 transition-transform group-hover:scale-110" />
              {!collapsed && <span className="truncate">{item.name}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Collapsed Toggle Button when collapsed */}
      {collapsed && (
        <div className="p-2 border-t border-[#1e3a5f] flex justify-center">
          <button
            onClick={() => setCollapsed(false)}
            className="p-2 rounded text-[#94a3b8] hover:text-white hover:bg-[#1e3a5f]/40"
            title="Expand sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Pipeline Status Mini-Indicator */}
      {!collapsed && (
        <div className="p-3 m-2 rounded-lg bg-[#0f1629] border border-[#1e3a5f]/60 text-xs font-mono">
          <div className="flex items-center justify-between text-[#64748b] mb-2">
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" /> Pipeline Status
            </span>
            <span className="text-[10px] text-amber-400 bg-amber-500/10 px-1 py-0.2 rounded border border-amber-500/20">
              DEMO
            </span>
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-[#94a3b8]">Kafka (9092)</span>
              <span className="text-gray-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                {demoSystemStatus.kafka.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#94a3b8]">Spark (7077)</span>
              <span className="text-gray-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                {demoSystemStatus.spark.status}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[#94a3b8]">Neo4j (7687)</span>
              <span className="text-gray-500 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-500"></span>
                {demoSystemStatus.neo4j.status}
              </span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
};
export default Sidebar;
