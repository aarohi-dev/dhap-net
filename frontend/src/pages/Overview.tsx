import React, { useState, useEffect } from 'react';
import {
  Activity,
  Server,
  Database,
  Cpu,
  AlertTriangle,
  Shield,
  Network,
  Zap,
  ArrowRight,
  Radio,
  Clock,
  Layers,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { demoSystemStatus, demoFlowEvents, demoAnomalies, demoAttackGraph } from '../data/fixtures';
import { formatBytes, protocolName, formatTime, getRiskColor, getRiskBg } from '../lib/utils';
import type { FlowEvent } from '../types';

// Daily red-team events from reports/data/redteam_per_day.csv
const REDTEAM_PER_DAY = [
  { day: 1, events: 10 },
  { day: 2, events: 15 },
  { day: 5, events: 21 },
  { day: 6, events: 3 },
  { day: 7, events: 1 },
  { day: 8, events: 273 }, // Major campaign
  { day: 9, events: 15 },
  { day: 12, events: 209 }, // Secondary campaign
  { day: 13, events: 81 },
  { day: 14, events: 35 },
  { day: 15, events: 26 },
  { day: 20, events: 1 },
  { day: 21, events: 4 },
  { day: 22, events: 1 },
  { day: 26, events: 26 },
  { day: 27, events: 9 },
  { day: 28, events: 3 },
  { day: 29, events: 16 },
];

export const Overview: React.FC = () => {
  // Polling simulated events list
  const [events, setEvents] = useState<FlowEvent[]>(demoFlowEvents.slice(0, 10));
  const [pollingCycle, setPollingCycle] = useState(0);

  // Poll every 5 seconds to simulate incoming stream
  useEffect(() => {
    const timer = setInterval(() => {
      setPollingCycle((prev) => prev + 1);
      setEvents((prev) => {
        // Pick an event to cycle in with current time
        const nextIdx = Math.floor(Math.random() * demoFlowEvents.length);
        const base = demoFlowEvents[nextIdx];
        const newEvent: FlowEvent = {
          ...base,
          id: `flow-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
          time: Math.floor(Date.now() / 1000),
        };
        return [newEvent, ...prev.slice(0, 9)];
      });
    }, 5000);

    return () => clearInterval(timer);
  }, []);

  const maxRedteam = Math.max(...REDTEAM_PER_DAY.map((d) => d.events));

  return (
    <div className="space-y-6">
      {/* Demo Mode Notice Banner */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 px-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <div className="text-xs">
            <span className="font-semibold text-amber-300 uppercase tracking-wider mr-2">Demo Mode Active:</span>
            <span className="text-[#cbd5e1]">
              Live Kafka (:9092), Spark (:7077), and Neo4j (:7687) infrastructure is offline. Serving pre-computed research pipeline results from LANL dataset.
            </span>
          </div>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 shrink-0 ml-2">
          REPORTS_DATA_SOURCE
        </span>
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-mono text-white tracking-tight flex items-center gap-2">
            <Shield className="w-6 h-6 text-cyan-400" />
            Security Intelligence Dashboard
          </h1>
          <p className="text-xs text-[#94a3b8] font-mono mt-1">
            Dynamic Hierarchical Attack-Path Network (DHAP-Net) • LANL Netflow Pipeline Monitoring
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-lg bg-[#0f1629] border border-[#1e3a5f] text-[#94a3b8]">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>Simulated Stream Active (5s)</span>
          </div>
        </div>
      </div>

      {/* 1. System Status Row (4 cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Kafka Ingestion */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 relative overflow-hidden transition-all hover:border-[#254d7a]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-blue-400" />
              Kafka Ingestion
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              OFFLINE
            </span>
          </div>
          <div className="font-mono text-base font-bold text-white mb-1">
            localhost:9092
          </div>
          <div className="text-xs font-mono text-[#94a3b8] flex justify-between">
            <span>Topic: <code className="text-cyan-400">dhapnet.flows</code></span>
            <span>Lag: 0 msgs</span>
          </div>
        </div>

        {/* Spark Streaming */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 relative overflow-hidden transition-all hover:border-[#254d7a]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              Spark Streaming
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              OFFLINE
            </span>
          </div>
          <div className="font-mono text-base font-bold text-white mb-1">
            spark://localhost:7077
          </div>
          <div className="text-xs font-mono text-[#94a3b8] flex justify-between">
            <span>Micro-batch: 0.5ms</span>
            <span>Workers: 0 active</span>
          </div>
        </div>

        {/* Graph Engine */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 relative overflow-hidden transition-all hover:border-[#254d7a]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-green-400" />
              Graph Engine
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
              OFFLINE
            </span>
          </div>
          <div className="font-mono text-base font-bold text-white mb-1">
            bolt://localhost:7687
          </div>
          <div className="text-xs font-mono text-[#94a3b8] flex justify-between">
            <span>Neo4j Bolt</span>
            <span>Target: 15k nodes</span>
          </div>
        </div>

        {/* Prediction Engine */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 relative overflow-hidden transition-all hover:border-[#254d7a]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-purple-400" />
              Prediction Engine
            </span>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-mono font-medium px-2 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              CACHED
            </span>
          </div>
          <div className="font-mono text-base font-bold text-white mb-1">
            PyTorch GeoTemporal
          </div>
          <div className="text-xs font-mono text-[#94a3b8] flex justify-between">
            <span>Checkpoints: 9</span>
            <span>A1 / A2 / A3</span>
          </div>
        </div>
      </div>

      {/* 2. Metrics Row (6 cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-3">
          <div className="text-[11px] text-[#94a3b8] uppercase tracking-wider font-semibold mb-1">Total Events</div>
          <div className="text-lg font-bold font-mono text-white">130,406,000</div>
          <div className="text-[10px] text-cyan-400 font-mono mt-0.5">LANL Netflow 130M</div>
        </div>

        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-3">
          <div className="text-[11px] text-[#94a3b8] uppercase tracking-wider font-semibold mb-1">Unique Hosts</div>
          <div className="text-lg font-bold font-mono text-white">15,488</div>
          <div className="text-[10px] text-[#94a3b8] font-mono mt-0.5">Observed in slice</div>
        </div>

        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-3">
          <div className="text-[11px] text-[#94a3b8] uppercase tracking-wider font-semibold mb-1">Red-Team Events</div>
          <div className="text-lg font-bold font-mono text-red-400">749</div>
          <div className="text-[10px] text-red-400/80 font-mono mt-0.5">Ground-truth tags</div>
        </div>

        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-3">
          <div className="text-[11px] text-[#94a3b8] uppercase tracking-wider font-semibold mb-1">Events Covered</div>
          <div className="text-lg font-bold font-mono text-green-400">663 / 749</div>
          <div className="text-[10px] text-green-400/80 font-mono mt-0.5">88.5% slice coverage</div>
        </div>

        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-3">
          <div className="text-[11px] text-[#94a3b8] uppercase tracking-wider font-semibold mb-1">Candidate Hosts</div>
          <div className="text-lg font-bold font-mono text-amber-400">1,248</div>
          <div className="text-[10px] text-amber-400/80 font-mono mt-0.5">K=2 hop BFS pool</div>
        </div>

        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-3">
          <div className="text-[11px] text-[#94a3b8] uppercase tracking-wider font-semibold mb-1">Prediction Window</div>
          <div className="text-lg font-bold font-mono text-white">15 Days</div>
          <div className="text-[10px] text-[#94a3b8] font-mono mt-0.5">1,296,000s horizon</div>
        </div>
      </div>

      {/* 3. Pipeline Flow Diagram */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-[#94a3b8] flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            End-to-End Processing Architecture
          </h2>
          <span className="text-[11px] font-mono text-[#64748b]">7 Pipeline Stages</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-7 gap-2 items-center">
          {/* Stage 1 */}
          <div className="bg-[#1a2a4a]/80 border border-[#3b82f6]/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-cyan-400 uppercase">Input</div>
            <div className="text-xs font-bold font-mono text-white mt-1">flows.txt</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">LANL (130M)</div>
          </div>

          <div className="hidden md:flex justify-center text-[#3b82f6]">
            <ArrowRight className="w-4 h-4" />
          </div>

          {/* Stage 2 */}
          <div className="bg-[#1a2a4a]/80 border border-[#3b82f6]/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-blue-400 uppercase">Ingest</div>
            <div className="text-xs font-bold font-mono text-white mt-1">Kafka Topic</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">dhapnet.flows</div>
          </div>

          <div className="hidden md:flex justify-center text-[#3b82f6]">
            <ArrowRight className="w-4 h-4" />
          </div>

          {/* Stage 3 */}
          <div className="bg-[#1a2a4a]/80 border border-[#3b82f6]/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-amber-400 uppercase">Streaming</div>
            <div className="text-xs font-bold font-mono text-white mt-1">Spark Engine</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">Micro-batch 0.5ms</div>
          </div>

          <div className="hidden md:flex justify-center text-[#3b82f6]">
            <ArrowRight className="w-4 h-4" />
          </div>

          {/* Stage 4 */}
          <div className="bg-[#1a2a4a]/80 border border-[#3b82f6]/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-green-400 uppercase">Graph Filter</div>
            <div className="text-xs font-bold font-mono text-white mt-1">GraphFrames</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">k-hop BFS (K=2)</div>
          </div>
        </div>

        {/* Second sub-row for stages 5-7 to connect seamlessly */}
        <div className="mt-3 pt-3 border-t border-[#1e3a5f]/60 grid grid-cols-1 md:grid-cols-5 gap-2 items-center">
          <div className="bg-[#1a2a4a]/80 border border-[#3b82f6]/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-purple-400 uppercase">Deep Learning</div>
            <div className="text-xs font-bold font-mono text-white mt-1">PyTorch GCN / A1</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">Temporal Link Pred</div>
          </div>

          <div className="hidden md:flex justify-center text-[#3b82f6]">
            <ArrowRight className="w-4 h-4" />
          </div>

          <div className="bg-[#1a2a4a]/80 border border-[#3b82f6]/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-cyan-400 uppercase">Graph DB</div>
            <div className="text-xs font-bold font-mono text-white mt-1">Neo4j Bolt</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">Attack Paths & Links</div>
          </div>

          <div className="hidden md:flex justify-center text-[#3b82f6]">
            <ArrowRight className="w-4 h-4" />
          </div>

          <div className="bg-[#1a2a4a]/80 border border-green-500/30 rounded-lg p-3 text-center">
            <div className="text-[10px] font-mono text-green-400 uppercase">Output</div>
            <div className="text-xs font-bold font-mono text-green-300 mt-1">Threat Predictions</div>
            <div className="text-[10px] text-[#94a3b8] mt-0.5">Ranked Risk Probs</div>
          </div>
        </div>
      </div>

      {/* 4. Two-Column Layout (Recent Network Events vs Recent Threat Intelligence) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column (7 cols): Live Network Events Table */}
        <div className="lg:col-span-7 bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Recent Network Events
                </h3>
                <p className="text-[11px] text-[#94a3b8] font-mono mt-0.5">
                  Live flow ingestion feed • Updating every 5s ({events.length} flows shown)
                </p>
              </div>
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/50 px-2 py-0.5 rounded">
                Cycle #{pollingCycle}
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-[#1e3a5f] text-[#94a3b8] text-[11px]">
                    <th className="pb-2 font-medium">TIMESTAMP</th>
                    <th className="pb-2 font-medium">SRC HOST</th>
                    <th className="pb-2 font-medium">DST HOST</th>
                    <th className="pb-2 font-medium">PROTO</th>
                    <th className="pb-2 font-medium text-right">BYTES</th>
                    <th className="pb-2 font-medium text-center">STATUS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1e3a5f]/40">
                  {events.map((evt) => {
                    const isFlagged = evt.dst_port === 445 || evt.dst_port === 3389 || evt.dst_port === 139;
                    return (
                      <tr key={evt.id} className="hover:bg-[#1a2a4a]/50 transition-colors">
                        <td className="py-2 text-[#94a3b8] whitespace-nowrap">
                          {formatTime(evt.time).split(',')[1] || formatTime(evt.time)}
                        </td>
                        <td className="py-2 text-cyan-400 font-semibold">{evt.src}</td>
                        <td className="py-2 text-white">{evt.dst}</td>
                        <td className="py-2">
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 border border-slate-700">
                            {protocolName(evt.protocol)}:{evt.dst_port}
                          </span>
                        </td>
                        <td className="py-2 text-right text-[#cbd5e1]">{formatBytes(evt.bytes_val)}</td>
                        <td className="py-2 text-center">
                          {isFlagged ? (
                            <span className="inline-flex items-center gap-1 text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30">
                              FLAGGED
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/30">
                              NORMAL
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1e3a5f] flex items-center justify-between text-xs text-[#94a3b8]">
            <span>Netflow Schema: time, duration, src, dst, src_port, dst_port, protocol, bytes</span>
            <Link to="/monitoring" className="text-cyan-400 hover:underline flex items-center gap-1">
              Live Monitor Stream <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
        </div>

        {/* Right Column (5 cols): Recent Threat Intelligence */}
        <div className="lg:col-span-5 bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-red-400" />
                  Recent Threat Intelligence
                </h3>
                <p className="text-[11px] text-[#94a3b8] font-mono mt-0.5">
                  Top prioritized anomaly events from model & BFS selection
                </p>
              </div>
              <Link to="/anomalies" className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
                View All <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="space-y-3">
              {demoAnomalies.slice(0, 5).map((anom) => {
                const riskLevel = anom.severity;
                const riskColor = getRiskColor(riskLevel);
                const riskBg = getRiskBg(riskLevel);

                return (
                  <div
                    key={anom.id}
                    className="p-3 rounded-lg bg-[#0a0e1a] border border-[#1e3a5f] hover:border-[#3b82f6]/50 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-white text-xs">{anom.host}</span>
                        <span
                          className={`text-[10px] uppercase font-mono px-1.5 py-0.5 rounded border ${riskBg} ${riskColor}`}
                        >
                          {anom.severity}
                        </span>
                      </div>
                      <span className="text-[11px] font-mono text-cyan-400 font-bold">
                        Score: {(anom.score * 100).toFixed(0)}%
                      </span>
                    </div>

                    <p className="text-xs text-[#cbd5e1] line-clamp-1">{anom.description}</p>

                    <div className="mt-2 flex items-center justify-between text-[10px] font-mono text-[#64748b]">
                      <span>Type: <code className="text-[#94a3b8]">{anom.type}</code></span>
                      <span>{new Date(anom.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1e3a5f] flex items-center justify-between text-xs text-[#94a3b8]">
            <span>Detection: GraphFrames BFS candidate selection (K=2)</span>
            <Link to="/graph" className="text-cyan-400 hover:underline flex items-center gap-1">
              Attack Graph <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* 5. Chart Row: Throughput Metric & Daily Red-Team Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Throughput Metric Gauge (4 cols) */}
        <div className="lg:col-span-4 bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              Ingestion Throughput
            </h3>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800 px-1.5 py-0.5 rounded">
              Historical Peak
            </span>
          </div>
          <p className="text-[11px] text-[#94a3b8] font-mono mb-4">
            Benchmark performance from <code>throughput.json</code>
          </p>

          <div className="text-center py-4 bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg mb-4">
            <div className="text-3xl font-extrabold font-mono text-cyan-400 tracking-tight">
              243,125
            </div>
            <div className="text-xs font-mono text-[#94a3b8] uppercase tracking-wider mt-1">
              Events / Second
            </div>
            <div className="text-[10px] text-[#64748b] font-mono mt-2">
              Replay Benchmark: 200 batches @ 0.50 ms/batch
            </div>
          </div>

          {/* Performance Bar */}
          <div className="space-y-1.5">
            <div className="flex justify-between text-xs font-mono text-[#94a3b8]">
              <span>Capacity Utilization</span>
              <span className="text-cyan-400 font-bold">81.0% (Peak: 300k/s)</span>
            </div>
            <div className="w-full bg-[#0a0e1a] rounded-full h-2.5 overflow-hidden border border-[#1e3a5f]">
              <div
                className="bg-gradient-to-r from-blue-500 to-cyan-400 h-2.5 rounded-full"
                style={{ width: '81%' }}
              />
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-[#1e3a5f] grid grid-cols-2 gap-2 text-center text-xs font-mono">
            <div className="bg-[#0a0e1a] p-2 rounded border border-[#1e3a5f]">
              <div className="text-[#94a3b8] text-[10px]">BATCH LATENCY</div>
              <div className="text-white font-bold mt-0.5">0.499 ms</div>
            </div>
            <div className="bg-[#0a0e1a] p-2 rounded border border-[#1e3a5f]">
              <div className="text-[#94a3b8] text-[10px]">TOTAL RUN TIME</div>
              <div className="text-white font-bold mt-0.5">0.100 s</div>
            </div>
          </div>
        </div>

        {/* Daily Red-Team Activity Bar Chart (8 cols) */}
        <div className="lg:col-span-8 bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
                <Shield className="w-4 h-4 text-red-400" />
                Red-Team Activity Timeline (LANL Dataset)
              </h3>
              <p className="text-[11px] text-[#94a3b8] font-mono mt-0.5">
                Ground truth compromise events per day from <code>redteam_per_day.csv</code> (749 total events)
              </p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-mono text-[#94a3b8]">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded bg-red-500" /> Peak Outbreaks (Day 8 & 12)
              </span>
            </div>
          </div>

          {/* Bar Chart Container */}
          <div className="mt-6 pt-4 pb-2">
            <div className="h-44 flex items-end gap-1.5 sm:gap-2 justify-between px-2">
              {REDTEAM_PER_DAY.map((item) => {
                const heightPct = Math.max(6, Math.round((item.events / maxRedteam) * 100));
                const isSpike = item.events > 100;

                return (
                  <div key={item.day} className="flex-1 flex flex-col items-center group relative h-full justify-end">
                    {/* Tooltip on hover */}
                    <div className="absolute -top-10 opacity-0 group-hover:opacity-100 transition-opacity bg-[#0a0e1a] border border-[#1e3a5f] text-white text-[10px] font-mono py-1 px-2 rounded shadow-lg pointer-events-none z-10 whitespace-nowrap">
                      Day {item.day}: <span className="text-red-400 font-bold">{item.events} events</span>
                    </div>

                    {/* Bar */}
                    <div
                      className={`w-full rounded-t transition-all duration-300 ${
                        isSpike
                          ? 'bg-gradient-to-t from-red-600 to-red-400 group-hover:from-red-500 group-hover:to-red-300 shadow-[0_0_10px_rgba(239,68,68,0.4)]'
                          : 'bg-gradient-to-t from-blue-600/70 to-cyan-500/70 group-hover:from-blue-500 group-hover:to-cyan-400'
                      }`}
                      style={{ height: `${heightPct}%` }}
                    />

                    {/* X-axis Day Label */}
                    <span className="text-[10px] font-mono text-[#64748b] group-hover:text-white mt-2">
                      D{item.day}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-[#1e3a5f] flex flex-col sm:flex-row justify-between items-center text-xs text-[#94a3b8] gap-2">
            <span>Critical surges: Day 8 (273 events) and Day 12 (209 events) represent lateral movement campaigns.</span>
            <span className="text-cyan-400 font-mono">Covered in 15d window: 663/749 (88.5%)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Overview;
