import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Search,
  Server,
  User,
  ShieldAlert,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Activity,
  Network,
  Clock,
  Radio,
  FileText,
  ExternalLink,
  ChevronRight,
  Filter,
} from 'lucide-react';
import { demoAttackGraph, demoFlowEvents, demoPredictions, demoAnomalies } from '@/data/fixtures';
import { formatBytes, formatTime, protocolName, getRiskColor, getRiskBg, getRiskLevel, formatProb } from '@/lib/utils';
import type { Host, FlowEvent, Prediction, AnomalyEvent } from '@/types';

export const EntityInvestigation: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const initialHost = searchParams.get('host') || '';
  const [searchQuery, setSearchQuery] = useState(initialHost);
  const [selectedEntity, setSelectedEntity] = useState<Host | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'activity' | 'graph' | 'predictions' | 'history'>('overview');
  const [filterType, setFilterType] = useState<string>('all');

  // Sync with URL params
  useEffect(() => {
    const hostParam = searchParams.get('host');
    if (hostParam) {
      setSearchQuery(hostParam);
      const found = demoAttackGraph.nodes.find((n) => n.id.toLowerCase() === hostParam.toLowerCase());
      if (found) {
        setSelectedEntity(found);
      }
    }
  }, [searchParams]);

  // Search Results
  const searchResults = useMemo(() => {
    let list = demoAttackGraph.nodes;

    if (filterType !== 'all') {
      list = list.filter((n) => n.type === filterType);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter((n) => n.id.toLowerCase().includes(q) || (n.ip && n.ip.includes(q)));
    }

    return list.slice(0, 20);
  }, [searchQuery, filterType]);

  // Associated flow events for selected host
  const entityFlows = useMemo(() => {
    if (!selectedEntity) return [];
    return demoFlowEvents.filter(
      (f) => f.src === selectedEntity.id || f.dst === selectedEntity.id
    );
  }, [selectedEntity]);

  // Associated predictions for selected host
  const entityPredictions = useMemo(() => {
    if (!selectedEntity) return [];
    return demoPredictions.filter((p) => p.host === selectedEntity.id);
  }, [selectedEntity]);

  // Associated anomalies for selected host
  const entityAnomalies = useMemo(() => {
    if (!selectedEntity) return [];
    return demoAnomalies.filter((a) => a.host === selectedEntity.id);
  }, [selectedEntity]);

  // 1-hop connected neighbors
  const connectedNeighbors = useMemo(() => {
    if (!selectedEntity) return [];
    const connectedIds = new Set<string>();

    demoAttackGraph.edges.forEach((e) => {
      const srcId = typeof e.source === 'object' ? (e.source as any).id : e.source;
      const tgtId = typeof e.target === 'object' ? (e.target as any).id : e.target;
      if (srcId === selectedEntity.id) connectedIds.add(tgtId);
      if (tgtId === selectedEntity.id) connectedIds.add(srcId);
    });

    return demoAttackGraph.nodes.filter((n) => connectedIds.has(n.id));
  }, [selectedEntity]);

  // Select an entity and update URL param
  const handleSelectEntity = (entity: Host) => {
    setSelectedEntity(entity);
    setSearchParams({ host: entity.id });
    setActiveTab('overview');
  };

  const handleBackToSearch = () => {
    setSelectedEntity(null);
    setSearchParams({});
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Search Header */}
      <div className="space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e3a5f] pb-4">
          <div>
            <h1 className="text-xl font-bold font-mono text-white flex items-center gap-2">
              <Radio className="w-5 h-5 text-cyan-400" />
              Entity Investigation
            </h1>
            <p className="text-xs text-[#94a3b8] font-mono mt-0.5">
              Deep telemetry inspection, neighborhood graph analysis &amp; lateral movement tracking
            </p>
          </div>

          {selectedEntity && (
            <button
              onClick={handleBackToSearch}
              className="px-3 py-1.5 bg-[#0f1629] hover:bg-[#131d35] border border-[#1e3a5f] text-gray-300 font-mono text-xs rounded transition flex items-center gap-1.5 self-start md:self-auto"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Entity Directory
            </button>
          )}
        </div>

        {/* Full-width Search Bar */}
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search host ID, IP, or user workstation (e.g. C1065, C2106, C17693, U620)..."
            className="w-full bg-[#0f1629] border border-[#1e3a5f] rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-[#64748b] focus:outline-none focus:border-cyan-500 font-mono shadow-inner"
          />
        </div>

        {/* Filter Badges */}
        <div className="flex items-center gap-2 text-xs font-mono overflow-x-auto pb-1">
          <span className="text-[#64748b] text-[11px] uppercase font-bold flex items-center gap-1">
            <Filter className="w-3 h-3" /> Filter:
          </span>
          {[
            { id: 'all', label: 'All Entities' },
            { id: 'compromised', label: '🔴 Compromised' },
            { id: 'predicted', label: '🟡 Predicted Risk' },
            { id: 'normal', label: '🔵 Normal' },
            { id: 'server', label: '🟣 Server' },
            { id: 'user', label: '🟢 User' },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterType(f.id)}
              className={`px-2.5 py-1 rounded text-xs transition ${
                filterType === f.id
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500 font-bold'
                  : 'bg-[#0f1629] text-[#94a3b8] hover:text-white border border-[#1e3a5f]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* VIEW 1: Entity Detail View */}
      {selectedEntity ? (
        <div className="space-y-6">
          {/* Entity Profile Banner */}
          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5 space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e3a5f] pb-4">
              <div className="flex items-center gap-3">
                <div
                  className={`w-12 h-12 rounded-lg flex items-center justify-center font-mono font-bold text-lg ${
                    selectedEntity.type === 'compromised'
                      ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                      : selectedEntity.type === 'predicted'
                      ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                      : 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                  }`}
                >
                  {selectedEntity.id.startsWith('U') ? <User className="w-6 h-6" /> : <Server className="w-6 h-6" />}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold font-mono text-white">{selectedEntity.id}</h2>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase ${
                        selectedEntity.type === 'compromised'
                          ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                          : selectedEntity.type === 'predicted'
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                      }`}
                    >
                      {selectedEntity.type}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase ${getRiskBg(
                        getRiskLevel(selectedEntity.risk_score)
                      )} ${getRiskColor(getRiskLevel(selectedEntity.risk_score))}`}
                    >
                      {getRiskLevel(selectedEntity.risk_score)} Risk
                    </span>
                  </div>
                  <p className="text-xs text-[#94a3b8] font-mono mt-0.5">
                    LANL Host Identifier | Hop Distance: {selectedEntity.hop_dist ?? 2} | In-Degree: {selectedEntity.in_degree} | Out-Degree: {selectedEntity.out_degree}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate(`/graph`)}
                  className="px-3 py-2 bg-[#172040] hover:bg-[#1e2a55] border border-[#1e3a5f] text-cyan-400 font-mono text-xs rounded transition flex items-center gap-1.5"
                >
                  <Network className="w-3.5 h-3.5" />
                  View in Attack Graph
                </button>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-[#1e3a5f] gap-1 overflow-x-auto text-xs font-mono">
              {[
                { id: 'overview', label: 'Overview', icon: FileText },
                { id: 'activity', label: `Network Activity (${entityFlows.length})`, icon: Activity },
                { id: 'graph', label: `Graph Neighborhood (${connectedNeighbors.length})`, icon: Network },
                { id: 'predictions', label: `Predictions (${entityPredictions.length})`, icon: Radio },
                { id: 'history', label: 'Timeline History', icon: Clock },
              ].map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`px-4 py-2 font-medium border-b-2 transition flex items-center gap-2 whitespace-nowrap ${
                      activeTab === tab.id
                        ? 'border-cyan-500 text-cyan-400 bg-[#131d35]'
                        : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#0a0e1a]'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* TAB 1: OVERVIEW */}
            {activeTab === 'overview' && (
              <div className="space-y-4 pt-2">
                {/* Stats Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 font-mono text-xs">
                  <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded">
                    <span className="text-[10px] text-[#64748b] uppercase">In-Degree</span>
                    <div className="text-lg font-bold text-white mt-0.5">{selectedEntity.in_degree}</div>
                    <span className="text-[10px] text-[#94a3b8]">Incoming connections</span>
                  </div>
                  <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded">
                    <span className="text-[10px] text-[#64748b] uppercase">Out-Degree</span>
                    <div className="text-lg font-bold text-white mt-0.5">{selectedEntity.out_degree}</div>
                    <span className="text-[10px] text-[#94a3b8]">Outgoing targets</span>
                  </div>
                  <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded">
                    <span className="text-[10px] text-[#64748b] uppercase">Ingress Volume</span>
                    <div className="text-lg font-bold text-cyan-400 mt-0.5">
                      {formatBytes(selectedEntity.bytes_in)}
                    </div>
                    <span className="text-[10px] text-[#94a3b8]">Netflow transferred</span>
                  </div>
                  <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded">
                    <span className="text-[10px] text-[#64748b] uppercase">Compromised Neighbors</span>
                    <div className="text-lg font-bold text-red-400 mt-0.5">
                      {selectedEntity.n_comp_nb ?? (selectedEntity.type === 'compromised' ? 3 : 1)}
                    </div>
                    <span className="text-[10px] text-[#94a3b8]">In 1-hop radius</span>
                  </div>
                </div>

                {/* Status Explanation */}
                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-4 space-y-2 text-xs font-mono">
                  <div className="font-bold text-white flex items-center gap-2">
                    <ShieldAlert className="w-4 h-4 text-cyan-400" />
                    Entity Profile &amp; Role Analysis
                  </div>
                  <p className="text-gray-300 leading-relaxed text-[11px]">
                    Host <strong>{selectedEntity.id}</strong> participates in enterprise NetFlow communications within the LANL comprehensive dataset.
                    {selectedEntity.type === 'compromised'
                      ? ' Confirmed red-team activity verified in authentication and process records. Serves as a primary lateral movement origin.'
                      : selectedEntity.type === 'predicted'
                      ? ' Identified as a candidate within K=2 hops of active breaches. Model assigns elevated likelihood of impending propagation.'
                      : ' Operating normally within baseline traffic expectations.'}
                  </p>
                  <div className="pt-2 border-t border-[#1e3a5f]/60 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] text-[#94a3b8]">
                    <div>Entropy: <span className="text-white font-bold">{selectedEntity.protocol_entropy ?? '0.55'}</span></div>
                    <div>Flows/Window: <span className="text-white font-bold">{selectedEntity.n_flows_w ?? '28'}</span></div>
                    <div>Hop Distance: <span className="text-white font-bold">{selectedEntity.hop_dist ?? '2'}</span></div>
                    <div>Dataset: <span className="text-white font-bold">LANL NetFlow 130M</span></div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: NETWORK ACTIVITY */}
            {activeTab === 'activity' && (
              <div className="space-y-3 pt-2">
                {entityFlows.length === 0 ? (
                  <div className="p-8 text-center text-xs font-mono text-[#64748b] bg-[#0a0e1a] rounded border border-[#1e3a5f]">
                    No explicit NetFlow records in sample buffer for {selectedEntity.id}.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-[#1e3a5f] bg-[#0a0e1a] text-[#64748b] text-[10px] uppercase">
                          <th className="py-2.5 px-3">Flow ID</th>
                          <th className="py-2.5 px-3">Direction</th>
                          <th className="py-2.5 px-3">Source</th>
                          <th className="py-2.5 px-3">Destination</th>
                          <th className="py-2.5 px-3">Protocol</th>
                          <th className="py-2.5 px-3">Dst Port</th>
                          <th className="py-2.5 px-3">Bytes</th>
                          <th className="py-2.5 px-3">Duration</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#1e3a5f]/40">
                        {entityFlows.map((f) => {
                          const isEgress = f.src === selectedEntity.id;
                          return (
                            <tr key={f.id} className="hover:bg-[#131d35] transition">
                              <td className="py-2 px-3 text-[#94a3b8]">{f.id}</td>
                              <td className="py-2 px-3">
                                <span
                                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                    isEgress
                                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                                      : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                                  }`}
                                >
                                  {isEgress ? 'OUT (Egress)' : 'IN (Ingress)'}
                                </span>
                              </td>
                              <td className="py-2 px-3 font-bold text-white">{f.src}</td>
                              <td className="py-2 px-3 font-bold text-white">{f.dst}</td>
                              <td className="py-2 px-3 text-[#94a3b8]">{protocolName(f.protocol)}</td>
                              <td className="py-2 px-3 text-cyan-300">{f.dst_port}</td>
                              <td className="py-2 px-3 font-semibold text-white">{formatBytes(f.bytes_val)}</td>
                              <td className="py-2 px-3 text-[#64748b]">{f.duration}s</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: GRAPH POSITION */}
            {activeTab === 'graph' && (
              <div className="space-y-4 pt-2">
                <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-white">
                      1-Hop Topology Neighborhood ({connectedNeighbors.length} adjacent entities)
                    </span>
                    <button
                      onClick={() => navigate(`/graph`)}
                      className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
                    >
                      Open in Full Explorer <ExternalLink className="w-3 h-3" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                    {connectedNeighbors.map((n) => (
                      <div
                        key={n.id}
                        onClick={() => handleSelectEntity(n)}
                        className="p-2.5 bg-[#0f1629] hover:bg-[#131d35] border border-[#1e3a5f] rounded-lg cursor-pointer transition flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2 font-mono text-xs">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              n.type === 'compromised'
                                ? 'bg-red-500'
                                : n.type === 'predicted'
                                ? 'bg-amber-500'
                                : 'bg-blue-500'
                            }`}
                          ></span>
                          <span className="font-bold text-white">{n.id}</span>
                        </div>
                        <span className="text-[10px] text-[#64748b] capitalize font-mono">{n.type}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: PREDICTIONS */}
            {activeTab === 'predictions' && (
              <div className="space-y-3 pt-2">
                {entityPredictions.length === 0 ? (
                  <div className="p-8 text-center text-xs font-mono text-[#64748b] bg-[#0a0e1a] rounded border border-[#1e3a5f]">
                    No explicit model predictions logged for {selectedEntity.id}.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {entityPredictions.map((p, idx) => (
                      <div
                        key={idx}
                        className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded-lg flex items-center justify-between font-mono text-xs"
                      >
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span>Model {p.model}</span>
                            <span className="text-[10px] bg-[#1e2a55] px-1.5 py-0.5 rounded text-cyan-300">
                              Horizon {p.delta}
                            </span>
                          </div>
                          <span className="text-[11px] text-[#94a3b8]">
                            Hop Distance: {p.hop_dist ?? 2} | Seed: {p.seed}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className="text-base font-bold text-amber-400">{formatProb(p.prob)}</div>
                          <span className="text-[10px] text-[#64748b]">Propagation Likelihood</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 5: TIMELINE HISTORY */}
            {activeTab === 'history' && (
              <div className="space-y-3 pt-2 font-mono text-xs">
                <div className="space-y-2 border-l-2 border-[#1e3a5f] pl-4 ml-2">
                  <div className="relative">
                    <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 absolute -left-[21px] top-1"></span>
                    <div className="text-[10px] text-[#64748b]">Day 1 — 00:00:00 UTC</div>
                    <div className="font-bold text-white">Entity Initialized in NetFlow Graph</div>
                    <p className="text-[11px] text-[#94a3b8]">First observed communication session recorded.</p>
                  </div>
                  <div className="relative pt-3">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400 absolute -left-[21px] top-4"></span>
                    <div className="text-[10px] text-[#64748b]">Day 3 — 08:14:22 UTC</div>
                    <div className="font-bold text-amber-300">k-Hop Candidate Generated</div>
                    <p className="text-[11px] text-[#94a3b8]">
                      GraphFrames BFS identifies host within 2 hops of breach origin (C1065).
                    </p>
                  </div>
                  {selectedEntity.type === 'compromised' && (
                    <div className="relative pt-3">
                      <span className="w-2.5 h-2.5 rounded-full bg-red-500 absolute -left-[21px] top-4"></span>
                      <div className="text-[10px] text-[#64748b]">Day 8 — 14:25:00 UTC</div>
                      <div className="font-bold text-red-400">🔴 Red-Team Compromise Confirmed</div>
                      <p className="text-[11px] text-[#94a3b8]">
                        Adversary lateral movement activity recorded in LANL red-team log.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* VIEW 2: Search Directory Grid */
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-mono text-[#94a3b8]">
            <span>Showing {searchResults.length} entities</span>
            <span>Click any card to inspect full profile</span>
          </div>

          {searchResults.length === 0 ? (
            <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-12 text-center space-y-3 font-mono">
              <AlertTriangle className="w-8 h-8 text-amber-400 mx-auto" />
              <h3 className="text-sm font-bold text-white">No hosts matching your search</h3>
              <p className="text-xs text-[#94a3b8] max-w-md mx-auto">
                LANL hosts use identifiers like <strong>C1065</strong>, <strong>C2106</strong>, <strong>C17693</strong>, or user endpoints like <strong>U620</strong>.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {searchResults.map((entity) => {
                const riskLvl = getRiskLevel(entity.risk_score);
                return (
                  <div
                    key={entity.id}
                    onClick={() => handleSelectEntity(entity)}
                    className="bg-[#0f1629] hover:bg-[#131d35] border border-[#1e3a5f] hover:border-cyan-500/50 rounded-lg p-4 cursor-pointer transition space-y-3 font-mono shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-3 h-3 rounded-full ${
                            entity.type === 'compromised'
                              ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]'
                              : entity.type === 'predicted'
                              ? 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
                              : 'bg-blue-500'
                          }`}
                        ></span>
                        <span className="text-base font-bold text-white">{entity.id}</span>
                      </div>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${getRiskBg(
                          riskLvl
                        )} ${getRiskColor(riskLvl)}`}
                      >
                        {riskLvl}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-[11px] pt-1 border-t border-[#1e3a5f]/40">
                      <div>
                        <span className="text-[10px] text-[#64748b] block">In/Out</span>
                        <span className="text-white font-semibold">
                          {entity.in_degree}/{entity.out_degree}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#64748b] block">Bytes In</span>
                        <span className="text-cyan-400 font-semibold">{formatBytes(entity.bytes_in)}</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[#64748b] block">Prob</span>
                        <span className="text-amber-400 font-semibold">{formatProb(entity.risk_score)}</span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-cyan-400 pt-1">
                      <span className="capitalize text-[#94a3b8] text-[10px]">{entity.type} entity</span>
                      <span className="flex items-center gap-1 hover:underline">
                        Inspect Profile <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default EntityInvestigation;
