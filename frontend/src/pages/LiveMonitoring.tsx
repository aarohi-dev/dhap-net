import React, { useState, useEffect, useMemo } from 'react';
import {
  Play,
  Pause,
  RotateCcw,
  RefreshCw,
  Activity,
  Server,
  Zap,
  Clock,
  Radio,
  Filter,
  Search,
  AlertTriangle,
  Layers,
  Database,
  Cpu,
  CheckCircle,
  XCircle,
  Copy,
} from 'lucide-react';
import { demoFlowEvents } from '../data/fixtures';
import { formatBytes, protocolName, formatTime } from '../lib/utils';
import type { FlowEvent } from '../types';

export const LiveMonitoring: React.FC = () => {
  // Event stream state
  const [events, setEvents] = useState<FlowEvent[]>(() => {
    // Generate initial 25 events based on fixtures with varied timestamps
    const initial: FlowEvent[] = [];
    const now = Math.floor(Date.now() / 1000);
    for (let i = 0; i < 25; i++) {
      const base = demoFlowEvents[i % demoFlowEvents.length];
      initial.push({
        ...base,
        id: `stream-init-${i}`,
        time: now - (25 - i) * 6,
        bytes_val: base.bytes_val + Math.floor(Math.random() * 5000),
      });
    }
    return initial.reverse(); // Most recent first
  });

  const [isStreaming, setIsStreaming] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [hostFilter, setHostFilter] = useState('');
  const [protocolFilter, setProtocolFilter] = useState<string>('all');
  const [timeFilter, setTimeFilter] = useState<string>('all');
  const [copiedCmd, setCopiedCmd] = useState(false);

  // Simulated live polling every 5s if stream is not paused
  useEffect(() => {
    if (!isStreaming) return;

    const interval = setInterval(() => {
      setEvents((prev) => {
        const randomFixture = demoFlowEvents[Math.floor(Math.random() * demoFlowEvents.length)];
        const newFlow: FlowEvent = {
          ...randomFixture,
          id: `flow-live-${Date.now()}`,
          time: Math.floor(Date.now() / 1000),
          bytes_val: Math.floor(Math.random() * 80000) + 512,
          packets: Math.floor(Math.random() * 40) + 2,
        };
        // Keep up to 50 rows
        return [newFlow, ...prev.slice(0, 49)];
      });
    }, 5000);

    return () => clearInterval(interval);
  }, [isStreaming]);

  // Handle control button clicks with real user feedback
  const handleAction = (actionName: string) => {
    console.log(`[StreamControl] Action triggered: ${actionName}`);
    setToastMessage(
      `Command unavailable: ${actionName}. Kafka producer at localhost:9092 is offline in demo mode.`
    );
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  const copyStartupCommand = () => {
    navigator.clipboard.writeText('docker compose up -d kafka spark neo4j && python pipeline/03_kafka_producer.py');
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2500);
  };

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter((evt) => {
      // Host filter
      if (hostFilter) {
        const query = hostFilter.toLowerCase();
        if (!evt.src.toLowerCase().includes(query) && !evt.dst.toLowerCase().includes(query)) {
          return false;
        }
      }
      // Protocol filter
      if (protocolFilter !== 'all') {
        const protoNum = parseInt(protocolFilter, 10);
        if (evt.protocol !== protoNum) {
          return false;
        }
      }
      // Time range filter
      if (timeFilter !== 'all') {
        const now = Math.floor(Date.now() / 1000);
        const ageSec = now - evt.time;
        if (timeFilter === '1h' && ageSec > 3600) return false;
        if (timeFilter === '24h' && ageSec > 86400) return false;
      }
      return true;
    });
  }, [events, hostFilter, protocolFilter, timeFilter]);

  return (
    <div className="space-y-6">
      {/* Toast Alert Notice */}
      {toastMessage && (
        <div className="bg-amber-500/20 border border-amber-500/50 rounded-lg p-3 text-xs font-mono text-amber-300 flex items-center justify-between shadow-lg animate-in fade-in slide-in-from-top duration-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-amber-400 hover:text-white px-2 py-0.5 rounded text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Header and Stream Control Bar */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#1e3a5f]">
          <div>
            <h1 className="text-xl font-bold font-mono text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-cyan-400" />
              Live Netflow Stream Monitor
            </h1>
            <p className="text-xs text-[#94a3b8] font-mono mt-1">
              Real-time ingestion and continuous feature extraction pipeline
            </p>
          </div>

          {/* Action Control Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => handleAction('Start Kafka Producer')}
              className="px-3 py-1.5 rounded-lg bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/40 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              Start Producer
            </button>

            <button
              onClick={() => {
                setIsStreaming(false);
                handleAction('Pause Stream');
              }}
              className="px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-500/40 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
            >
              <Pause className="w-3.5 h-3.5 fill-current" />
              Pause
            </button>

            <button
              onClick={() => {
                setIsStreaming(true);
                handleAction('Resume Stream');
              }}
              className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/40 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Resume
            </button>

            <button
              onClick={() => {
                handleAction('Refresh Buffer');
                setEvents((prev) => [...prev]);
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
          </div>
        </div>

        {/* Status Callout */}
        <div className="mt-3 flex flex-col sm:flex-row sm:items-center justify-between text-xs font-mono text-[#94a3b8] gap-2">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span>
              Controls connect to Kafka producer at <code>localhost:9092</code> — unavailable in demo mode.
            </span>
          </div>
          <span className="text-[#64748b]">
            Simulation State: <span className={isStreaming ? 'text-green-400 font-bold' : 'text-amber-400 font-bold'}>{isStreaming ? 'ACTIVE (5s polling)' : 'PAUSED'}</span>
          </span>
        </div>
      </div>

      {/* Stream Health Panel (4 Status Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Kafka Ingestion Status */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-blue-400" />
              Kafka Status
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              OFFLINE
            </span>
          </div>
          <div className="font-mono text-base font-bold text-white mb-1">
            localhost:9092
          </div>
          <div className="text-xs font-mono text-[#94a3b8]">
            Topic: <span className="text-cyan-400">dhapnet.flows</span>
          </div>
        </div>

        {/* Spark Structured Streaming */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Spark Status
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              OFFLINE
            </span>
          </div>
          <div className="font-mono text-base font-bold text-white mb-1">
            spark://localhost:7077
          </div>
          <div className="text-xs font-mono text-[#94a3b8]">
            Workers: 0 active • 0 jobs
          </div>
        </div>

        {/* Historical Events/sec */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Replay Speed
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
              BENCHMARK
            </span>
          </div>
          <div className="font-mono text-xl font-bold text-cyan-400 mb-1">
            243,125 /s
          </div>
          <div className="text-xs font-mono text-[#94a3b8]">
            from <code className="text-slate-300">throughput.json</code>
          </div>
        </div>

        {/* Batch Latency */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-purple-400" />
              Batch Latency
            </span>
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/30">
              MICRO-BATCH
            </span>
          </div>
          <div className="font-mono text-xl font-bold text-green-400 mb-1">
            0.50 ms
          </div>
          <div className="text-xs font-mono text-[#94a3b8]">
            200 batches in 0.10s total
          </div>
        </div>
      </div>

      {/* Processing Pipeline Status Breakdown (6 stages) */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-[#94a3b8] mb-3 flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          Processing Pipeline Stage Health
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          {/* Stage 1 */}
          <div className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold font-mono text-white">flows.txt</span>
              <span className="w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="text-[10px] text-red-400 font-mono">Offline</div>
            <div className="text-[10px] text-[#64748b] mt-1">Raw file producer</div>
          </div>

          {/* Stage 2 */}
          <div className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold font-mono text-white">Kafka Topic</span>
              <span className="w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="text-[10px] text-red-400 font-mono">Offline</div>
            <div className="text-[10px] text-[#64748b] mt-1">dhapnet.flows:9092</div>
          </div>

          {/* Stage 3 */}
          <div className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold font-mono text-white">Spark Stream</span>
              <span className="w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="text-[10px] text-red-400 font-mono">Offline</div>
            <div className="text-[10px] text-[#64748b] mt-1">Micro-batch processing</div>
          </div>

          {/* Stage 4 */}
          <div className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold font-mono text-white">GraphFrames</span>
              <span className="w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="text-[10px] text-red-400 font-mono">Offline</div>
            <div className="text-[10px] text-[#64748b] mt-1">k-hop BFS candidate filter</div>
          </div>

          {/* Stage 5 */}
          <div className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold font-mono text-white">PyTorch Inference</span>
              <span className="w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="text-[10px] text-red-400 font-mono">Offline</div>
            <div className="text-[10px] text-[#64748b] mt-1">GCN / temporal prediction</div>
          </div>

          {/* Stage 6 */}
          <div className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] flex flex-col justify-between">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold font-mono text-white">Neo4j Export</span>
              <span className="w-2 h-2 rounded-full bg-red-500" />
            </div>
            <div className="text-[10px] text-red-400 font-mono">Offline</div>
            <div className="text-[10px] text-[#64748b] mt-1">Graph persistence (:7687)</div>
          </div>
        </div>

        {/* Startup Instruction */}
        <div className="mt-4 pt-3 border-t border-[#1e3a5f] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono">
          <div className="text-[#94a3b8] flex items-center gap-2">
            <span className="text-cyan-400 font-semibold">Live Pipeline Startup:</span>
            <code className="bg-[#0a0e1a] px-2 py-1 rounded text-slate-300 border border-[#1e3a5f]">
              docker compose up -d kafka spark neo4j && python pipeline/03_kafka_producer.py
            </code>
          </div>
          <button
            onClick={copyStartupCommand}
            className="text-xs text-cyan-400 hover:text-white flex items-center gap-1 shrink-0"
          >
            <Copy className="w-3.5 h-3.5" />
            {copiedCmd ? 'Copied!' : 'Copy Command'}
          </button>
        </div>
      </div>

      {/* Event Stream Filter Bar */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Host Search Filter */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter by host (e.g. C1065)..."
              value={hostFilter}
              onChange={(e) => setHostFilter(e.target.value)}
              className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-white placeholder-[#64748b] focus:outline-none focus:border-cyan-500 w-52"
            />
          </div>

          {/* Protocol Dropdown */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-[#94a3b8]">Protocol:</span>
            <select
              value={protocolFilter}
              onChange={(e) => setProtocolFilter(e.target.value)}
              className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Protocols</option>
              <option value="6">TCP (6)</option>
              <option value="17">UDP (17)</option>
              <option value="1">ICMP (1)</option>
            </select>
          </div>

          {/* Time Range Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-[#94a3b8]">Window:</span>
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Available</option>
              <option value="1h">Last 1 Hour</option>
              <option value="24h">Last 24 Hours</option>
            </select>
          </div>
        </div>

        <div className="text-xs font-mono text-[#94a3b8]">
          Showing <span className="text-white font-bold">{filteredEvents.length}</span> of {events.length} buffered events
        </div>
      </div>

      {/* Incoming Event Stream Table */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg overflow-hidden">
        <div className="p-4 border-b border-[#1e3a5f] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white">
              Continuous Flow Event Buffer
            </h2>
          </div>
          <span className="text-[11px] font-mono text-[#64748b]">
            Ring Buffer (Max 50 Rows) • Auto-scrolling
          </span>
        </div>

        <div className="overflow-x-auto max-h-[500px]">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#0a0e1a] sticky top-0 border-b border-[#1e3a5f] text-[#94a3b8] text-[11px]">
              <tr>
                <th className="py-2.5 px-4 font-medium">#</th>
                <th className="py-2.5 px-4 font-medium">TIMESTAMP</th>
                <th className="py-2.5 px-4 font-medium">SOURCE</th>
                <th className="py-2.5 px-4 font-medium">DESTINATION</th>
                <th className="py-2.5 px-4 font-medium">PROTOCOL</th>
                <th className="py-2.5 px-4 font-medium text-right">PACKETS</th>
                <th className="py-2.5 px-4 font-medium text-right">BYTES</th>
                <th className="py-2.5 px-4 font-medium text-center">SOURCE TYPE</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e3a5f]/40">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-[#64748b] font-mono">
                    No flow events match the current filter criteria.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((evt, idx) => {
                  const isRedteamTarget =
                    evt.dst === 'C1065' || evt.dst === 'C2106' || evt.dst === 'C17693';

                  return (
                    <tr
                      key={evt.id}
                      className="hover:bg-[#1a2a4a]/50 transition-colors duration-150"
                    >
                      <td className="py-2 px-4 text-[#64748b]">{idx + 1}</td>
                      <td className="py-2 px-4 text-[#94a3b8] whitespace-nowrap">
                        {formatTime(evt.time)}
                      </td>
                      <td className="py-2 px-4 font-bold text-cyan-400">
                        {evt.src}
                        <span className="text-[10px] text-[#64748b] ml-1">:{evt.src_port}</span>
                      </td>
                      <td className="py-2 px-4 font-bold text-white">
                        {evt.dst}
                        <span className="text-[10px] text-[#64748b] ml-1">:{evt.dst_port}</span>
                      </td>
                      <td className="py-2 px-4">
                        <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 border border-slate-700">
                          {protocolName(evt.protocol)}
                        </span>
                      </td>
                      <td className="py-2 px-4 text-right text-[#cbd5e1]">{evt.packets}</td>
                      <td className="py-2 px-4 text-right text-cyan-300">{formatBytes(evt.bytes_val)}</td>
                      <td className="py-2 px-4 text-center">
                        {isRedteamTarget ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
                            [REPLAY_COMPROMISED]
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            [REPLAY_NORMAL]
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default LiveMonitoring;
