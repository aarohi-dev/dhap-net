import React, { useState, useRef, useMemo, useCallback } from 'react';
import ForceGraph2D, { ForceGraphMethods } from 'react-force-graph-2d';
import {
  Search,
  Filter,
  RotateCcw,
  Info,
  AlertTriangle,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  X,
  ExternalLink,
  Layers,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { demoAttackGraph } from '@/data/fixtures';
import { getRiskLevel, getRiskColor, getRiskBg, formatProb, formatBytes } from '@/lib/utils';
import type { Host, Edge, HostType } from '@/types';

// Extended type for graph nodes with simulation coordinates
interface GraphNode extends Host {
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number;
  fy?: number;
}

interface GraphLink extends Omit<Edge, 'source' | 'target'> {
  source: string | GraphNode;
  target: string | GraphNode;
}

export const AttackGraph: React.FC = () => {
  const navigate = useNavigate();
  const graphRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(undefined);

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  // Filters
  const [typeFilters, setTypeFilters] = useState<Record<string, boolean>>({
    compromised: true,
    predicted: true,
    normal: true,
    server: true,
    user: true,
  });

  const [edgeFilters, setEdgeFilters] = useState<Record<string, boolean>>({
    COMMUNICATES_WITH: true,
    COMPROMISED: true,
    SIMULATED_PROPAGATION: true,
  });

  const [riskFilter, setRiskFilter] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');
  const [dagMode, setDagMode] = useState<string | null>(null);
  const [cypherExpanded, setCypherExpanded] = useState(false);
  const [copiedQuery, setCopiedQuery] = useState(false);

  // Prepare and filter data
  const filteredData = useMemo(() => {
    // Filter nodes
    const nodes = (demoAttackGraph.nodes as GraphNode[]).filter((node) => {
      // Type filter
      if (!typeFilters[node.type]) return false;

      // Risk filter
      const level = getRiskLevel(node.risk_score);
      if (riskFilter === 'critical' && level !== 'critical') return false;
      if (riskFilter === 'high' && level !== 'critical' && level !== 'high') return false;
      if (riskFilter === 'medium' && (level === 'low' || level === 'none')) return false;
      if (riskFilter === 'low' && level === 'none') return false;

      return true;
    });

    const activeNodeIds = new Set(nodes.map((n) => n.id));

    // Filter links
    const links = (demoAttackGraph.edges as GraphLink[]).filter((edge) => {
      // Relationship type filter
      if (!edgeFilters[edge.relationship]) return false;

      const srcId = typeof edge.source === 'object' ? (edge.source as GraphNode).id : edge.source;
      const tgtId = typeof edge.target === 'object' ? (edge.target as GraphNode).id : edge.target;

      return activeNodeIds.has(srcId) && activeNodeIds.has(tgtId);
    });

    return { nodes, links };
  }, [typeFilters, edgeFilters, riskFilter]);

  // Node highlighting helper
  const isMatchSearch = useCallback(
    (node: GraphNode) => {
      if (!searchQuery.trim()) return false;
      return node.id.toLowerCase().includes(searchQuery.trim().toLowerCase());
    },
    [searchQuery]
  );

  // Custom Canvas Node Renderer
  const renderNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isSelected = selectedNode?.id === node.id;
      const isHovered = hoveredNode?.id === node.id;
      const isSearchMatch = isMatchSearch(node);

      // Node size based on type and degree
      let radius = 6;
      if (node.type === 'compromised') radius = 10;
      else if (node.type === 'predicted') radius = 8;
      else if (node.type === 'server') radius = 11;
      else if (node.type === 'user') radius = 6;

      // Degree proportional scaling
      const degree = (node.in_degree || 0) + (node.out_degree || 0);
      radius += Math.min(degree * 0.25, 6);

      const x = node.x ?? 0;
      const y = node.y ?? 0;

      // Colors
      let fillColor = '#3b82f6'; // normal blue
      let strokeColor = '#1d4ed8';

      if (node.type === 'compromised') {
        fillColor = '#ef4444'; // red
        strokeColor = '#b91c1c';
      } else if (node.type === 'predicted') {
        fillColor = '#f59e0b'; // amber
        strokeColor = '#d97706';
      } else if (node.type === 'server') {
        fillColor = '#8b5cf6'; // purple
        strokeColor = '#6d28d9';
      } else if (node.type === 'user') {
        fillColor = '#06b6d4'; // cyan
        strokeColor = '#0891b2';
      }

      // Outer Glow / Ring for compromised or predicted or selected
      if (node.type === 'compromised' || isSelected || isSearchMatch) {
        ctx.beginPath();
        ctx.arc(x, y, radius + 4, 0, 2 * Math.PI, false);
        ctx.fillStyle = node.type === 'compromised' ? 'rgba(239, 68, 68, 0.25)' : 'rgba(59, 130, 246, 0.3)';
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = node.type === 'compromised' ? '#ef4444' : '#60a5fa';
        ctx.stroke();
      } else if (node.type === 'predicted') {
        ctx.beginPath();
        ctx.arc(x, y, radius + 3, 0, 2 * Math.PI, false);
        ctx.fillStyle = 'rgba(245, 158, 11, 0.2)';
        ctx.fill();
      }

      // Main Node Circle
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, 2 * Math.PI, false);
      ctx.fillStyle = fillColor;
      ctx.fill();
      ctx.lineWidth = isSelected ? 2.5 : 1.2;
      ctx.strokeStyle = isSelected ? '#ffffff' : strokeColor;
      ctx.stroke();

      // Node Label
      const label = node.id;
      const fontSize = Math.max(10 / globalScale, 3);
      ctx.font = `${isSelected || isSearchMatch ? 'bold ' : ''}${fontSize}px 'JetBrains Mono', monospace`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';

      if (isSelected || isSearchMatch || globalScale > 1.2 || node.type === 'compromised' || node.type === 'predicted') {
        ctx.fillStyle = isSelected ? '#ffffff' : isSearchMatch ? '#fbbf24' : '#cbd5e1';
        ctx.fillText(label, x, y + radius + 3);
      }
    },
    [selectedNode, hoveredNode, isMatchSearch]
  );

  // Link Styling Accessors
  const getLinkColor = useCallback((link: GraphLink) => {
    switch (link.relationship) {
      case 'COMPROMISED':
        return '#ef4444';
      case 'SIMULATED_PROPAGATION':
        return '#f59e0b';
      case 'COMMUNICATES_WITH':
      default:
        return 'rgba(75, 85, 99, 0.5)';
    }
  }, []);

  const getLinkWidth = useCallback((link: GraphLink) => {
    switch (link.relationship) {
      case 'COMPROMISED':
        return 3;
      case 'SIMULATED_PROPAGATION':
        return 2;
      case 'COMMUNICATES_WITH':
      default:
        return 1;
    }
  }, []);

  // Reset view to fit all nodes
  const handleResetView = () => {
    graphRef.current?.zoomToFit(400, 40);
  };

  // Connected nodes of selected entity
  const connectedNodes = useMemo(() => {
    if (!selectedNode) return [];
    const connectedIds = new Set<string>();

    demoAttackGraph.edges.forEach((e) => {
      const srcId = typeof e.source === 'object' ? (e.source as GraphNode).id : e.source;
      const tgtId = typeof e.target === 'object' ? (e.target as GraphNode).id : e.target;
      if (srcId === selectedNode.id) connectedIds.add(tgtId);
      if (tgtId === selectedNode.id) connectedIds.add(srcId);
    });

    return demoAttackGraph.nodes.filter((n) => connectedIds.has(n.id));
  }, [selectedNode]);

  // Derived attack path for selected node
  const attackPath = useMemo(() => {
    if (!selectedNode) return [];
    if (selectedNode.type === 'compromised') {
      return ['Patient Zero: C1065', selectedNode.id === 'C1065' ? 'Foothold Confirmed' : `Propagated to ${selectedNode.id}`];
    }
    if (selectedNode.type === 'predicted') {
      // Find incoming edges
      const incoming = demoAttackGraph.edges.find((e) => {
        const tgtId = typeof e.target === 'object' ? (e.target as GraphNode).id : e.target;
        return tgtId === selectedNode.id;
      });
      if (incoming) {
        const srcId = typeof incoming.source === 'object' ? (incoming.source as GraphNode).id : incoming.source;
        return ['C1065 (Foothold)', `${srcId} (Compromised)`, `${selectedNode.id} (Predicted Target)`];
      }
    }
    return [];
  }, [selectedNode]);

  const cypherQuery = `// Query Simulated Propagation Attack Paths
MATCH (n:Host)-[r:SIMULATED_PROPAGATION]->(m:Host)
RETURN n.host_id AS source, r.propagation_prob AS prob, m.host_id AS target
ORDER BY r.propagation_prob DESC
LIMIT 100;

// Query Multi-hop Breach Reachability
MATCH p=(c:Host {is_compromised: true})-[*1..3]->(target:Host)
WHERE target.is_compromised = false
RETURN p LIMIT 25;`;

  const copyCypher = () => {
    navigator.clipboard.writeText(cypherQuery);
    setCopiedQuery(true);
    setTimeout(() => setCopiedQuery(false), 2000);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden bg-[#0a0e1a] text-[#e2e8f0]">
      {/* Top Banner */}
      <div className="bg-[#0f1629] border-b border-[#1e3a5f] px-4 py-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-white tracking-wide uppercase font-mono">
            Attack Graph Explorer
          </span>
          <span className="text-[#64748b]">|</span>
          <span className="text-[#94a3b8]">Interactive Multi-Stage Propagation Topology</span>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            <span className="text-red-400 font-medium">5 Compromised</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span className="text-amber-400 font-medium">7 Predicted Risk</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            <span className="text-blue-400 font-medium">{filteredData.nodes.length} Visible Nodes</span>
          </div>
        </div>
      </div>

      {/* Main 3-Column Content Body */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* LEFT COLUMN: Controls Panel (280px) */}
        <div className="w-[280px] bg-[#0f1629] border-r border-[#1e3a5f] flex flex-col p-4 overflow-y-auto space-y-4 text-xs shrink-0 z-10">
          {/* Search Box */}
          <div>
            <label className="text-[11px] font-mono text-[#94a3b8] block mb-1.5 uppercase font-medium">
              Search Host
            </label>
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#64748b]" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="e.g. C1065, C2106..."
                className="w-full bg-[#0a0e1a] border border-[#1e3a5f] rounded pl-8 pr-7 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-2 text-[#64748b] hover:text-white"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            {searchQuery && (
              <p className="text-[10px] text-cyan-400 mt-1 font-mono">
                Matching nodes highlighted on canvas
              </p>
            )}
          </div>

          {/* Node Type Filters */}
          <div className="border-t border-[#1e3a5f]/60 pt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-mono text-[#94a3b8] uppercase font-medium">
                Node Types
              </span>
              <Filter className="w-3 h-3 text-[#64748b]" />
            </div>
            <div className="space-y-1.5">
              {[
                { id: 'compromised', label: 'Compromised (Red-Team)', color: 'bg-red-500' },
                { id: 'predicted', label: 'Predicted Risk (A1 Model)', color: 'bg-amber-500' },
                { id: 'normal', label: 'Normal Workstation', color: 'bg-blue-500' },
                { id: 'server', label: 'High-Degree Server', color: 'bg-purple-500' },
                { id: 'user', label: 'User Endpoint', color: 'bg-cyan-500' },
              ].map((item) => (
                <label key={item.id} className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={typeFilters[item.id]}
                    onChange={(e) =>
                      setTypeFilters((prev) => ({ ...prev, [item.id]: e.target.checked }))
                    }
                    className="rounded bg-[#0a0e1a] border-[#1e3a5f] text-cyan-500 focus:ring-0 w-3.5 h-3.5"
                  />
                  <span className={`w-2 h-2 rounded-full ${item.color}`}></span>
                  <span className="text-gray-300 text-[11px]">{item.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Edge Filters */}
          <div className="border-t border-[#1e3a5f]/60 pt-3">
            <span className="text-[11px] font-mono text-[#94a3b8] block mb-2 uppercase font-medium">
              Edge Relationships
            </span>
            <div className="space-y-1.5">
              {[
                {
                  id: 'COMPROMISED',
                  label: 'COMPROMISED (Observed)',
                  style: 'border-b-2 border-red-500 w-4',
                },
                {
                  id: 'SIMULATED_PROPAGATION',
                  label: 'SIMULATED_PROPAGATION',
                  style: 'border-b-2 border-dashed border-amber-500 w-4',
                },
                {
                  id: 'COMMUNICATES_WITH',
                  label: 'COMMUNICATES_WITH (Flow)',
                  style: 'border-b border-gray-500 w-4',
                },
              ].map((item) => (
                <label key={item.id} className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={edgeFilters[item.id]}
                    onChange={(e) =>
                      setEdgeFilters((prev) => ({ ...prev, [item.id]: e.target.checked }))
                    }
                    className="rounded bg-[#0a0e1a] border-[#1e3a5f] text-cyan-500 focus:ring-0 w-3.5 h-3.5"
                  />
                  <span className={item.style}></span>
                  <span className="text-gray-300 text-[11px]">{item.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Risk Level Filter */}
          <div className="border-t border-[#1e3a5f]/60 pt-3">
            <span className="text-[11px] font-mono text-[#94a3b8] block mb-1.5 uppercase font-medium">
              Risk Severity
            </span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value as any)}
              className="w-full bg-[#0a0e1a] border border-[#1e3a5f] rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="all">All Risk Levels</option>
              <option value="critical">Critical Only (≥ 80%)</option>
              <option value="high">High &amp; Critical (≥ 60%)</option>
              <option value="medium">Medium, High &amp; Critical (≥ 40%)</option>
              <option value="low">Any Active Risk (≥ 10%)</option>
            </select>
          </div>

          {/* Layout Mode */}
          <div className="border-t border-[#1e3a5f]/60 pt-3">
            <span className="text-[11px] font-mono text-[#94a3b8] block mb-1.5 uppercase font-medium">
              Graph Layout
            </span>
            <div className="grid grid-cols-2 gap-1.5">
              <button
                onClick={() => setDagMode(null)}
                className={`py-1 px-2 rounded text-[11px] font-mono border ${
                  dagMode === null
                    ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                    : 'bg-[#0a0e1a] border-[#1e3a5f] text-gray-400 hover:text-white'
                }`}
              >
                Force-Directed
              </button>
              <button
                onClick={() => setDagMode('radialout')}
                className={`py-1 px-2 rounded text-[11px] font-mono border ${
                  dagMode === 'radialout'
                    ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300'
                    : 'bg-[#0a0e1a] border-[#1e3a5f] text-gray-400 hover:text-white'
                }`}
              >
                Radial Out
              </button>
            </div>
          </div>

          {/* Graph Actions */}
          <div className="border-t border-[#1e3a5f]/60 pt-3">
            <button
              onClick={handleResetView}
              className="w-full flex items-center justify-center gap-1.5 bg-[#172040] hover:bg-[#1e2a55] border border-[#1e3a5f] text-cyan-400 py-1.5 px-3 rounded font-mono text-xs transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset View / Zoom
            </button>
          </div>

          {/* Topology Stats */}
          <div className="mt-auto border-t border-[#1e3a5f]/60 pt-3 text-[11px] text-[#94a3b8] space-y-1 font-mono">
            <div className="flex justify-between">
              <span>Nodes:</span>
              <span className="text-white font-medium">{filteredData.nodes.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Edges:</span>
              <span className="text-white font-medium">{filteredData.links.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Density:</span>
              <span className="text-cyan-400">0.076</span>
            </div>
          </div>
        </div>

        {/* CENTER: ForceGraph2D Canvas */}
        <div className="flex-1 flex flex-col relative bg-[#0a0e1a]">
          <ForceGraph2D
            ref={graphRef}
            graphData={filteredData}
            nodeId="id"
            nodeCanvasObject={renderNode}
            nodePointerAreaPaint={(node: GraphNode, color, ctx) => {
              ctx.fillStyle = color;
              ctx.beginPath();
              ctx.arc(node.x ?? 0, node.y ?? 0, 14, 0, 2 * Math.PI, false);
              ctx.fill();
            }}
            linkColor={getLinkColor}
            linkWidth={getLinkWidth}
            linkLineDash={(link: GraphLink) =>
              link.relationship === 'SIMULATED_PROPAGATION' ? [4, 2] : null
            }
            linkDirectionalParticles={(link: GraphLink) =>
              link.relationship === 'SIMULATED_PROPAGATION' ? 2 : 0
            }
            linkDirectionalParticleSpeed={0.006}
            linkDirectionalParticleWidth={2.5}
            linkDirectionalParticleColor={() => '#f59e0b'}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={0.95}
            backgroundColor="#0a0e1a"
            dagMode={dagMode as any}
            dagLevelDistance={80}
            d3VelocityDecay={0.3}
            onNodeClick={(node: GraphNode) => {
              setSelectedNode(node);
              graphRef.current?.centerAt(node.x, node.y, 400);
            }}
            onNodeHover={(node: GraphNode | null) => setHoveredNode(node)}
            cooldownTicks={100}
            onEngineStop={() => {
              // initial auto zoom once simulation stabilizes
            }}
          />

          {/* Graph Watermark / Overlay Legend */}
          <div className="absolute top-3 right-3 bg-[#0f1629]/80 backdrop-blur-sm border border-[#1e3a5f] rounded px-3 py-2 text-[11px] font-mono text-gray-300 pointer-events-none flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span> Confirmed
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span> Predicted Risk
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span> Normal Host
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span> Server
            </span>
          </div>

          {/* Hover Tooltip Overlay if hovered */}
          {hoveredNode && !selectedNode && (
            <div
              className="absolute bottom-4 left-4 bg-[#0f1629]/90 border border-[#1e3a5f] rounded-lg p-2.5 text-xs font-mono shadow-xl pointer-events-none"
            >
              <div className="font-bold text-white flex items-center gap-2">
                <span>{hoveredNode.id}</span>
                <span className="text-[10px] text-cyan-400 capitalize">({hoveredNode.type})</span>
              </div>
              <div className="text-[#94a3b8] text-[11px]">
                Risk Score: <span className="text-amber-400 font-semibold">{formatProb(hoveredNode.risk_score)}</span>
              </div>
              <div className="text-[#64748b] text-[10px]">
                In: {hoveredNode.in_degree} | Out: {hoveredNode.out_degree}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Entity Detail Panel (320px) */}
        {selectedNode && (
          <div className="w-[320px] bg-[#0f1629] border-l border-[#1e3a5f] flex flex-col p-4 overflow-y-auto space-y-4 text-xs shrink-0 z-10 shadow-2xl">
            {/* Header */}
            <div className="flex items-start justify-between border-b border-[#1e3a5f] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white font-mono">{selectedNode.id}</h3>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                      selectedNode.type === 'compromised'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                        : selectedNode.type === 'predicted'
                        ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                        : 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                    }`}
                  >
                    {selectedNode.type}
                  </span>
                </div>
                <p className="text-[11px] text-[#94a3b8] font-mono mt-0.5">LANL NetFlow Entity</p>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-[#94a3b8] hover:text-white p-1 rounded hover:bg-[#1e2a55]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Status & Warning Notice */}
            {selectedNode.type === 'compromised' ? (
              <div className="bg-red-950/40 border border-red-800/60 rounded-md p-2.5 text-[11px] text-red-300 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-red-400">
                  <ShieldAlert className="w-4 h-4" />
                  🔴 CONFIRMED COMPROMISE
                </div>
                <p className="text-[10px] leading-tight text-red-200">
                  Red-team adversary activity observed in LANL authentication &amp; flow logs.
                </p>
              </div>
            ) : selectedNode.type === 'predicted' ? (
              <div className="bg-amber-950/40 border border-amber-800/60 rounded-md p-2.5 text-[11px] text-amber-300 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-400">
                  <AlertTriangle className="w-4 h-4" />
                  ⚠️ SIMULATED PROPAGATION
                </div>
                <p className="text-[10px] leading-tight text-amber-200">
                  This is a model prediction, not an observed network event. Source: DHAP-Net A1 model on LANL netflow dataset.
                </p>
              </div>
            ) : null}

            {/* Risk Assessment */}
            <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-[#94a3b8] font-mono">Propagation Risk</span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${getRiskBg(
                    getRiskLevel(selectedNode.risk_score)
                  )} ${getRiskColor(getRiskLevel(selectedNode.risk_score))}`}
                >
                  {getRiskLevel(selectedNode.risk_score)}
                </span>
              </div>
              <div className="space-y-1">
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-white font-bold">{formatProb(selectedNode.risk_score)}</span>
                  <span className="text-[#64748b]">CI: [78.4% - 92.1%]</span>
                </div>
                <div className="w-full bg-[#1e2a55] h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${
                      selectedNode.risk_score >= 0.8
                        ? 'bg-red-500'
                        : selectedNode.risk_score >= 0.6
                        ? 'bg-amber-500'
                        : 'bg-blue-500'
                    }`}
                    style={{ width: `${selectedNode.risk_score * 100}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Graph Metrics */}
            <div className="grid grid-cols-2 gap-2 font-mono">
              <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-2.5 rounded">
                <div className="text-[10px] text-[#64748b]">In-Degree</div>
                <div className="text-sm font-bold text-white mt-0.5">{selectedNode.in_degree}</div>
              </div>
              <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-2.5 rounded">
                <div className="text-[10px] text-[#64748b]">Out-Degree</div>
                <div className="text-sm font-bold text-white mt-0.5">{selectedNode.out_degree}</div>
              </div>
              <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-2.5 rounded">
                <div className="text-[10px] text-[#64748b]">Bytes Ingress</div>
                <div className="text-sm font-bold text-cyan-400 mt-0.5">
                  {formatBytes(selectedNode.bytes_in)}
                </div>
              </div>
              <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-2.5 rounded">
                <div className="text-[10px] text-[#64748b]">Hop Distance</div>
                <div className="text-sm font-bold text-amber-400 mt-0.5">
                  {selectedNode.hop_dist ?? 2}
                </div>
              </div>
            </div>

            {/* Attack Path Traceback */}
            {attackPath.length > 0 && (
              <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-3 space-y-2">
                <div className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-400 font-semibold">
                  <Zap className="w-3.5 h-3.5" />
                  Estimated Attack Reachability Path
                </div>
                <div className="space-y-1.5 font-mono text-[11px]">
                  {attackPath.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-1.5">
                      <span className="w-4 h-4 rounded-full bg-[#1e2a55] text-cyan-300 text-[10px] flex items-center justify-center font-bold">
                        {idx + 1}
                      </span>
                      <span className={idx === attackPath.length - 1 ? 'text-amber-300 font-bold' : 'text-gray-300'}>
                        {step}
                      </span>
                      {idx < attackPath.length - 1 && (
                        <ArrowRight className="w-3 h-3 text-[#64748b] ml-auto" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Connected Entities */}
            <div>
              <span className="text-[11px] font-mono text-[#94a3b8] block mb-1.5 uppercase font-medium">
                Connected Hosts ({connectedNodes.length})
              </span>
              <div className="space-y-1 max-h-36 overflow-y-auto pr-1">
                {connectedNodes.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => {
                      setSelectedNode(n as GraphNode);
                      graphRef.current?.centerAt((n as GraphNode).x, (n as GraphNode).y, 400);
                    }}
                    className="w-full flex items-center justify-between p-1.5 rounded bg-[#0a0e1a] hover:bg-[#172040] border border-[#1e3a5f]/60 text-left font-mono text-[11px] transition"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          n.type === 'compromised'
                            ? 'bg-red-500'
                            : n.type === 'predicted'
                            ? 'bg-amber-500'
                            : 'bg-blue-500'
                        }`}
                      ></span>
                      <span className="text-white">{n.id}</span>
                    </div>
                    <span className="text-[10px] text-[#64748b] capitalize">{n.type}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Jump to Entity Investigation */}
            <div className="pt-2">
              <button
                onClick={() => navigate(`/entities?host=${selectedNode.id}`)}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-mono py-2 px-3 rounded text-xs font-semibold shadow-md transition"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                Investigate Entity Profile
              </button>
            </div>
          </div>
        )}
      </div>

      {/* BOTTOM: Expandable Cypher Query Panel */}
      <div className="bg-[#0f1629] border-t border-[#1e3a5f] z-20">
        <button
          onClick={() => setCypherExpanded(!cypherExpanded)}
          className="w-full px-4 py-2 flex items-center justify-between text-xs text-[#94a3b8] hover:text-white hover:bg-[#131d35] font-mono transition"
        >
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span className="font-semibold text-white">Neo4j Cypher Graph Queries</span>
            <span className="text-[#64748b]">bolt://localhost:7687 (user: neo4j, pass: dhapnet2024)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-cyan-400">
              {cypherExpanded ? 'Collapse' : 'Expand Live Cypher Console'}
            </span>
            {cypherExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </div>
        </button>

        {cypherExpanded && (
          <div className="p-4 bg-[#0a0e1a] border-t border-[#1e3a5f] space-y-3">
            <div className="relative">
              <pre className="bg-[#050811] border border-[#1e3a5f] rounded-lg p-3 text-xs font-mono text-cyan-300 overflow-x-auto leading-relaxed">
                {cypherQuery}
              </pre>
              <button
                onClick={copyCypher}
                className="absolute top-2.5 right-2.5 bg-[#172040] hover:bg-[#1e2a55] border border-[#1e3a5f] text-gray-300 hover:text-white px-2.5 py-1 rounded text-[11px] font-mono flex items-center gap-1.5 transition"
              >
                {copiedQuery ? (
                  <>
                    <Check className="w-3 h-3 text-green-400" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy Cypher</span>
                  </>
                )}
              </button>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono text-[#64748b]">
              <span>Graph schema: (n:Host)-[r:SIMULATED_PROPAGATION|COMMUNICATES_WITH|COMPROMISED]-&gt;(m:Host)</span>
              <span>Dataset: LANL NetFlow 130M records</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AttackGraph;
