import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  Shield,
  Search,
  Filter,
  Eye,
  CheckCircle,
  XCircle,
  ArrowRight,
  ExternalLink,
  Info,
  Server,
  Network,
  Share2,
  X,
  Radio,
  Sliders,
  ChevronRight,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { demoAnomalies, demoAttackGraph, demoFlowEvents } from '../data/fixtures';
import { formatBytes, formatTime, getRiskColor, getRiskBg } from '../lib/utils';
import type { AnomalyEvent, Host } from '../types';

export const AnomalyDetection: React.FC = () => {
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>(demoAnomalies);
  const [selectedAnomaly, setSelectedAnomaly] = useState<AnomalyEvent | null>(demoAnomalies[0]);
  const [searchHost, setSearchHost] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Filtered anomalies
  const filteredAnomalies = useMemo(() => {
    return anomalies.filter((a) => {
      if (searchHost && !a.host.toLowerCase().includes(searchHost.toLowerCase())) {
        return false;
      }
      if (severityFilter !== 'all' && a.severity !== severityFilter) {
        return false;
      }
      if (typeFilter !== 'all' && a.type !== typeFilter) {
        return false;
      }
      return true;
    });
  }, [anomalies, searchHost, severityFilter, typeFilter]);

  // Find host metadata for the selected anomaly
  const selectedHostMeta: Host | undefined = useMemo(() => {
    if (!selectedAnomaly) return undefined;
    return demoAttackGraph.nodes.find((n) => n.id === selectedAnomaly.host);
  }, [selectedAnomaly]);

  // Connected hosts for selected anomaly
  const connectedHosts = useMemo(() => {
    if (!selectedAnomaly) return [];
    const hostId = selectedAnomaly.host;
    const connected = new Set<string>();
    demoAttackGraph.edges.forEach((e) => {
      if (e.source === hostId) connected.add(e.target);
      if (e.target === hostId) connected.add(e.source);
    });
    return Array.from(connected);
  }, [selectedAnomaly]);

  // Helper to determine status tag (CONFIRMED vs PREDICTED vs CANDIDATE)
  const getCompromiseBadge = (hostId: string) => {
    const node = demoAttackGraph.nodes.find((n) => n.id === hostId);
    if (!node) return { text: 'CANDIDATE', style: 'bg-slate-800 text-slate-300 border-slate-700' };

    if (node.type === 'compromised') {
      return { text: 'CONFIRMED', style: 'bg-red-500/20 text-red-400 border-red-500/40 glow-red' };
    }
    if (node.type === 'predicted') {
      return { text: 'PREDICTED', style: 'bg-blue-500/20 text-blue-400 border-blue-500/40 glow-blue' };
    }
    return { text: 'CANDIDATE', style: 'bg-slate-800 text-slate-300 border-slate-700' };
  };

  // Toggle acknowledge state
  const toggleAcknowledge = (id: string) => {
    setAnomalies((prev) =>
      prev.map((a) => (a.id === id ? { ...a, acknowledged: !a.acknowledged } : a))
    );
    if (selectedAnomaly && selectedAnomaly.id === id) {
      setSelectedAnomaly((curr) => (curr ? { ...curr, acknowledged: !curr.acknowledged } : null));
    }
    setToastMessage(`Anomaly status updated for ${selectedAnomaly?.host || id}.`);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleEscalate = () => {
    setToastMessage(`Incident for host ${selectedAnomaly?.host} escalated to Tier-2 SOC!`);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Counts
  const totalCount = anomalies.length;
  const criticalCount = anomalies.filter((a) => a.severity === 'critical').length;
  const highCount = anomalies.filter((a) => a.severity === 'high').length;
  const investigatingCount = anomalies.filter((a) => !a.acknowledged).length;

  return (
    <div className="space-y-6">
      {/* Toast Notice */}
      {toastMessage && (
        <div className="bg-blue-600/20 border border-blue-500/50 rounded-lg p-3 text-xs font-mono text-blue-300 flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-blue-400 shrink-0" />
            <span>{toastMessage}</span>
          </div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-blue-400 hover:text-white px-2 py-0.5 rounded text-[11px]"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Top Source Notice & Legend */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            <div className="text-xs">
              <span className="font-bold text-white uppercase tracking-wider block mb-0.5">
                GraphFrames BFS Candidate Selection:
              </span>
              <p className="text-[#cbd5e1] leading-relaxed">
                Anomaly candidates are hosts within <span className="text-cyan-400 font-mono font-semibold">K=2 hops</span> of confirmed compromised hosts, identified via GraphFrames BFS on the LANL netflow dataset. These are candidate risk profiles undergoing dynamic scoring, not all are confirmed breach events.
              </p>
            </div>
          </div>
        </div>

        {/* Status Legend */}
        <div className="pt-2.5 border-t border-[#1e3a5f] flex flex-wrap items-center gap-4 text-xs font-mono">
          <span className="text-[#94a3b8] uppercase text-[11px] font-semibold">Entity Classification:</span>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]" />
            <span className="text-red-400 font-bold">CONFIRMED</span>
            <span className="text-[#64748b]">(Red-team ground truth)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
            <span className="text-blue-400 font-bold">PREDICTED</span>
            <span className="text-[#64748b]">(PyTorch model risk)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
            <span className="text-slate-300 font-bold">CANDIDATE</span>
            <span className="text-[#64748b]">(BFS reachable K=2)</span>
          </div>
        </div>
      </div>

      {/* Summary Stat Cards (4 Cards) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
          <div className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider mb-1">
            Total Anomalies
          </div>
          <div className="text-2xl font-bold font-mono text-white">{totalCount}</div>
          <div className="text-[11px] text-[#64748b] font-mono mt-0.5">Identified candidates</div>
        </div>

        <div className="bg-[#0f1629] border border-red-500/30 rounded-lg p-4 glow-red">
          <div className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Critical Severity</span>
            <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-red-400">{criticalCount}</div>
          <div className="text-[11px] text-red-400/70 font-mono mt-0.5">Immediate threat level</div>
        </div>

        <div className="bg-[#0f1629] border border-amber-500/30 rounded-lg p-4">
          <div className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>High Severity</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400">{highCount}</div>
          <div className="text-[11px] text-amber-400/70 font-mono mt-0.5">Elevated risk posture</div>
        </div>

        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
          <div className="text-xs font-semibold text-cyan-400 uppercase tracking-wider mb-1 flex items-center justify-between">
            <span>Investigating</span>
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">{investigatingCount}</div>
          <div className="text-[11px] text-[#64748b] font-mono mt-0.5">Unacknowledged triage</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Host Filter */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search host (e.g. C1065)..."
              value={searchHost}
              onChange={(e) => setSearchHost(e.target.value)}
              className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg pl-9 pr-3 py-1.5 text-xs font-mono text-white placeholder-[#64748b] focus:outline-none focus:border-cyan-500 w-48"
            />
          </div>

          {/* Severity Dropdown */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-[#94a3b8]">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          {/* Type / Method Dropdown */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-mono text-[#94a3b8]">Type:</span>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg px-2.5 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Anomaly Types</option>
              <option value="lateral_movement">Lateral Movement</option>
              <option value="c2_comm">C2 Communication</option>
              <option value="scanning">Port/Subnet Scanning</option>
              <option value="privilege_esc">Privilege Escalation</option>
              <option value="exfiltration">Data Exfiltration</option>
            </select>
          </div>
        </div>

        <div className="text-xs font-mono text-[#94a3b8]">
          Showing <span className="text-cyan-400 font-bold">{filteredAnomalies.length}</span> matching anomalies
        </div>
      </div>

      {/* Main Content: Table + Slide-in Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Anomaly Table (7 or 12 cols depending on selection) */}
        <div
          className={`${
            selectedAnomaly ? 'lg:col-span-7' : 'lg:col-span-12'
          } bg-[#0f1629] border border-[#1e3a5f] rounded-lg overflow-hidden transition-all duration-200`}
        >
          <div className="p-4 border-b border-[#1e3a5f] flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              Prioritized Anomaly Feed
            </h2>
            <span className="text-xs font-mono text-[#94a3b8]">
              Click row to investigate host
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#0a0e1a] border-b border-[#1e3a5f] text-[#94a3b8] text-[11px]">
                <tr>
                  <th className="py-2.5 px-4 font-medium">SEVERITY</th>
                  <th className="py-2.5 px-4 font-medium">HOST</th>
                  <th className="py-2.5 px-4 font-medium">CLASSIFICATION</th>
                  <th className="py-2.5 px-4 font-medium">ANOMALY TYPE</th>
                  <th className="py-2.5 px-4 font-medium text-right">SCORE</th>
                  <th className="py-2.5 px-4 font-medium text-center">STATUS</th>
                  <th className="py-2.5 px-4 font-medium text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e3a5f]/40">
                {filteredAnomalies.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-[#64748b] font-mono">
                      No anomalies match the selected filters.
                    </td>
                  </tr>
                ) : (
                  filteredAnomalies.map((anom) => {
                    const badge = getCompromiseBadge(anom.host);
                    const isSelected = selectedAnomaly?.id === anom.id;
                    const riskColor = getRiskColor(anom.severity);
                    const riskBg = getRiskBg(anom.severity);

                    return (
                      <tr
                        key={anom.id}
                        onClick={() => setSelectedAnomaly(anom)}
                        className={`cursor-pointer transition-colors duration-150 ${
                          isSelected
                            ? 'bg-[#1a2a4a] border-l-2 border-l-cyan-400'
                            : 'hover:bg-[#1a2a4a]/40'
                        }`}
                      >
                        {/* Severity */}
                        <td className="py-3 px-4">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${riskBg} ${riskColor}`}
                          >
                            {anom.severity}
                          </span>
                        </td>

                        {/* Host */}
                        <td className="py-3 px-4 font-bold text-white text-sm">
                          {anom.host}
                        </td>

                        {/* Classification */}
                        <td className="py-3 px-4">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${badge.style}`}
                          >
                            {badge.text}
                          </span>
                        </td>

                        {/* Type */}
                        <td className="py-3 px-4 text-[#cbd5e1]">
                          <span className="capitalize">{anom.type.replace('_', ' ')}</span>
                        </td>

                        {/* Anomaly Score Bar */}
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <span className="font-bold text-cyan-400">
                              {(anom.score * 100).toFixed(0)}%
                            </span>
                            <div className="w-12 bg-[#0a0e1a] rounded-full h-1.5 overflow-hidden border border-[#1e3a5f]">
                              <div
                                className={`h-1.5 rounded-full ${
                                  anom.score > 0.8
                                    ? 'bg-red-500'
                                    : anom.score > 0.6
                                    ? 'bg-amber-400'
                                    : 'bg-blue-400'
                                }`}
                                style={{ width: `${anom.score * 100}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="py-3 px-4 text-center">
                          {anom.acknowledged ? (
                            <span className="text-[10px] text-[#64748b] bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                              TRIAGED
                            </span>
                          ) : (
                            <span className="text-[10px] text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800">
                              ACTIVE
                            </span>
                          )}
                        </td>

                        {/* Action */}
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedAnomaly(anom);
                            }}
                            className="text-xs text-cyan-400 hover:text-white px-2 py-1 rounded bg-[#0a0e1a] hover:bg-[#1a2a4a] border border-[#1e3a5f] transition-colors"
                          >
                            Investigate
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Slide-in Detail Panel (5 cols) */}
        {selectedAnomaly && (
          <div className="lg:col-span-5 bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5 space-y-4 animate-in fade-in duration-200">
            {/* Detail Header */}
            <div className="flex items-start justify-between pb-3 border-b border-[#1e3a5f]">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-2xl font-extrabold font-mono text-white tracking-tight">
                    {selectedAnomaly.host}
                  </h3>
                  {(() => {
                    const badge = getCompromiseBadge(selectedAnomaly.host);
                    return (
                      <span
                        className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded border ${badge.style}`}
                      >
                        {badge.text}
                      </span>
                    );
                  })()}
                </div>
                <div className="text-xs text-[#94a3b8] font-mono flex items-center gap-2">
                  <span>Incident ID: <code>{selectedAnomaly.id}</code></span>
                  <span>•</span>
                  <span>{new Date(selectedAnomaly.timestamp).toLocaleString()}</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedAnomaly(null)}
                className="text-[#64748b] hover:text-white p-1 rounded hover:bg-[#1a2a4a] transition-colors"
                title="Close panel"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Severity and Score Meter */}
            <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-[#94a3b8]">THREAT SEVERITY</span>
                <span
                  className={`text-xs font-mono font-bold uppercase px-2 py-0.5 rounded border ${getRiskBg(
                    selectedAnomaly.severity
                  )} ${getRiskColor(selectedAnomaly.severity)}`}
                >
                  {selectedAnomaly.severity}
                </span>
              </div>

              <div>
                <div className="flex items-center justify-between text-xs font-mono mb-1">
                  <span className="text-[#94a3b8]">ANOMALY RISK SCORE</span>
                  <span className="text-cyan-400 font-bold">
                    {(selectedAnomaly.score * 100).toFixed(1)} / 100
                  </span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-[#1e3a5f]">
                  <div
                    className={`h-2 rounded-full ${
                      selectedAnomaly.score > 0.8
                        ? 'bg-red-500'
                        : selectedAnomaly.score > 0.6
                        ? 'bg-amber-400'
                        : 'bg-blue-400'
                    }`}
                    style={{ width: `${selectedAnomaly.score * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Description */}
            <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-3.5">
              <div className="text-[10px] font-mono uppercase text-[#64748b] tracking-wider mb-1">
                EVIDENCE SUMMARY
              </div>
              <p className="text-xs text-[#cbd5e1] leading-relaxed">
                {selectedAnomaly.description}
              </p>
            </div>

            {/* Detection Attribution Note */}
            <div className="p-3 rounded-lg bg-blue-950/20 border border-blue-900/40 text-[11px] font-mono text-[#94a3b8] space-y-1">
              <div>
                <span className="text-cyan-400 font-semibold">Detection Method:</span> k-hop BFS candidate selection (K=2 hops from confirmed compromised footholds).
              </div>
              <div>
                <span className="text-cyan-400 font-semibold">Source:</span> GraphFrames BFS on LANL netflow dataset (130M records).
              </div>
            </div>

            {/* Graph Features Table */}
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-white mb-2 flex items-center justify-between">
                <span>Extracted Graph Features</span>
                <span className="text-[10px] font-mono text-[#64748b]">reports/data/candidates_all</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-2.5">
                  <div className="text-[10px] text-[#94a3b8]">HOP DIST FROM REDTEAM</div>
                  <div className="text-base font-bold text-cyan-400 mt-0.5">
                    {selectedHostMeta?.hop_dist ?? 2} Hops
                  </div>
                </div>

                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-2.5">
                  <div className="text-[10px] text-[#94a3b8]">COMPROMISED NEIGHBORS</div>
                  <div className="text-base font-bold text-red-400 mt-0.5">
                    {selectedHostMeta?.n_comp_nb ?? 1} Hosts
                  </div>
                </div>

                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-2.5">
                  <div className="text-[10px] text-[#94a3b8]">IN-DEGREE / OUT-DEGREE</div>
                  <div className="text-white font-bold mt-0.5">
                    {selectedHostMeta?.in_degree ?? 4} in / {selectedHostMeta?.out_degree ?? 6} out
                  </div>
                </div>

                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-2.5">
                  <div className="text-[10px] text-[#94a3b8]">BYTES INGESTED</div>
                  <div className="text-white font-bold mt-0.5">
                    {formatBytes(selectedHostMeta?.bytes_in ?? 131072)}
                  </div>
                </div>

                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-2.5">
                  <div className="text-[10px] text-[#94a3b8]">PROTOCOL ENTROPY</div>
                  <div className="text-white font-bold mt-0.5">
                    {selectedHostMeta?.protocol_entropy?.toFixed(2) ?? '0.65'}
                  </div>
                </div>

                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-2.5">
                  <div className="text-[10px] text-[#94a3b8]">WINDOW FLOW COUNT</div>
                  <div className="text-white font-bold mt-0.5">
                    {selectedHostMeta?.n_flows_w ?? 28} Flows
                  </div>
                </div>
              </div>
            </div>

            {/* Connected Entities */}
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-white mb-2">
                1-Hop Connected Hosts ({connectedHosts.length})
              </div>
              <div className="flex flex-wrap gap-1.5">
                {connectedHosts.length === 0 ? (
                  <span className="text-xs font-mono text-[#64748b]">No direct connections in slice.</span>
                ) : (
                  connectedHosts.map((peer) => {
                    const peerBadge = getCompromiseBadge(peer);
                    return (
                      <span
                        key={peer}
                        className={`text-xs font-mono px-2 py-0.5 rounded border ${peerBadge.style}`}
                      >
                        {peer}
                      </span>
                    );
                  })
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="pt-3 border-t border-[#1e3a5f] flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleAcknowledge(selectedAnomaly.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-colors border ${
                    selectedAnomaly.acknowledged
                      ? 'bg-slate-800 text-slate-300 border-slate-700'
                      : 'bg-green-600/20 text-green-400 border-green-500/40 hover:bg-green-600/30'
                  }`}
                >
                  {selectedAnomaly.acknowledged ? 'Mark Active' : 'Mark Acknowledged'}
                </button>

                <button
                  onClick={handleEscalate}
                  className="px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/40 text-xs font-mono font-medium transition-colors"
                >
                  Escalate Incident
                </button>
              </div>

              <Link
                to={`/entities?search=${selectedAnomaly.host}`}
                className="text-xs font-mono text-cyan-400 hover:text-white flex items-center gap-1"
              >
                Full Profile <ArrowRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnomalyDetection;
