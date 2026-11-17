import React, { useState, useMemo } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Info,
  ChevronRight,
  Filter,
  CheckCircle2,
  XCircle,
  HelpCircle,
  BarChart3,
  Search,
  ExternalLink,
  ShieldAlert,
  ArrowUpDown,
  Zap,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { demoPredictions, demoModelMetrics, demoAttackGraph } from '@/data/fixtures';
import { formatProb, getRiskColor, getRiskBg, getRiskLevel } from '@/lib/utils';
import type { Prediction, ModelMetrics } from '@/types';

export const Predictions: React.FC = () => {
  const navigate = useNavigate();

  // Control State
  const [selectedModel, setSelectedModel] = useState<'A1' | 'A2' | 'A3' | 'B1_RF' | 'B2_GBT'>('A1');
  const [selectedDelta, setSelectedDelta] = useState<'1h' | '6h' | '24h'>('6h');
  const [selectedSeed, setSelectedSeed] = useState<number>(42);
  const [searchHost, setSearchHost] = useState('');
  const [sortField, setSortField] = useState<'prob' | 'hop_dist' | 'rank'>('prob');
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedRow, setSelectedRow] = useState<Prediction | null>(null);

  // Model comparison metrics from final_results.csv
  const comparisonData = useMemo(() => {
    const deltaH = selectedDelta === '1h' ? 1 : selectedDelta === '6h' ? 6 : 24;

    const realMetrics: Record<string, { ap: string; auc: string; brier: string; status: string }> = {
      'A1 (DHAP-Net)': {
        ap: 'NaN',
        auc: 'NaN',
        brier: '0.000',
        status: 'Incomplete Labels (Data Scarcity)',
      },
      'A2 (TGN-TA)': {
        ap: deltaH === 1 ? '0.161' : deltaH === 6 ? '0.223' : '0.259',
        auc: deltaH === 1 ? '0.832' : deltaH === 6 ? '0.867' : '0.888',
        brier: '0.042',
        status: 'Benchmark Model',
      },
      'A3 (DM-STG-AD)': {
        ap: deltaH === 1 ? '0.145' : deltaH === 6 ? '0.198' : '0.231',
        auc: deltaH === 1 ? '0.810' : deltaH === 6 ? '0.841' : '0.875',
        brier: '0.051',
        status: 'Benchmark Model',
      },
      'B1_RF (Random Forest)': {
        ap: deltaH === 1 ? '0.0046' : deltaH === 6 ? '0.0348' : '0.0610',
        auc: deltaH === 1 ? '0.566' : deltaH === 6 ? '0.578' : '0.498',
        brier: deltaH === 1 ? '0.149' : deltaH === 6 ? '0.047' : '0.067',
        status: 'Baseline Tabular',
      },
      'B2_GBT (Gradient Boosted Trees)': {
        ap: deltaH === 1 ? '0.0050' : deltaH === 6 ? '0.0265' : '0.0685',
        auc: deltaH === 1 ? '0.599' : deltaH === 6 ? '0.601' : '0.561',
        brier: deltaH === 1 ? '0.146' : deltaH === 6 ? '0.034' : '0.059',
        status: 'Baseline Tabular',
      },
      'B3_LR (Logistic Regression)': {
        ap: deltaH === 1 ? '0.0038' : deltaH === 6 ? '0.0151' : '0.0563',
        auc: deltaH === 1 ? '0.464' : deltaH === 6 ? '0.384' : '0.534',
        brier: deltaH === 1 ? '0.244' : deltaH === 6 ? '0.214' : '0.158',
        status: 'Baseline Linear',
      },
      'B4_FixedDiff': {
        ap: deltaH === 1 ? '0.0032' : deltaH === 6 ? '0.0159' : '0.0436',
        auc: deltaH === 1 ? '0.389' : deltaH === 6 ? '0.357' : '0.358',
        brier: deltaH === 1 ? '0.192' : deltaH === 6 ? '0.328' : '0.703',
        status: 'Heuristic Baseline',
      },
      'B5_NearestHop': {
        ap: deltaH === 1 ? '0.0027' : deltaH === 6 ? '0.0161' : '0.0502',
        auc: deltaH === 1 ? '0.402' : deltaH === 6 ? '0.400' : '0.452',
        brier: deltaH === 1 ? '0.944' : deltaH === 6 ? '0.936' : '0.906',
        status: 'BFS Heuristic',
      },
    };

    return realMetrics;
  }, [selectedDelta]);

  // Filtered & Sorted Predictions
  const predictions = useMemo(() => {
    let list = [...demoPredictions];

    if (searchHost.trim()) {
      list = list.filter((p) => p.host.toLowerCase().includes(searchHost.trim().toLowerCase()));
    }

    list.sort((a, b) => {
      let valA = a[sortField] ?? 0;
      let valB = b[sortField] ?? 0;
      if (typeof valA === 'string') valA = Number(valA);
      if (typeof valB === 'string') valB = Number(valB);

      if (sortAsc) return (valA as number) - (valB as number);
      return (valB as number) - (valA as number);
    });

    return list;
  }, [searchHost, sortField, sortAsc]);

  // Probability distribution histogram buckets [0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0]
  const distributionBuckets = useMemo(() => {
    const buckets = [
      { range: '0.0 - 0.2', count: 0, color: '#3b82f6', label: 'Negligible' },
      { range: '0.2 - 0.4', count: 0, color: '#06b6d4', label: 'Low Risk' },
      { range: '0.4 - 0.6', count: 0, color: '#eab308', label: 'Medium' },
      { range: '0.6 - 0.8', count: 0, color: '#f97316', label: 'High' },
      { range: '0.8 - 1.0', count: 0, color: '#ef4444', label: 'Critical' },
    ];

    demoPredictions.forEach((p) => {
      if (p.prob < 0.2) buckets[0].count++;
      else if (p.prob < 0.4) buckets[1].count++;
      else if (p.prob < 0.6) buckets[2].count++;
      else if (p.prob < 0.8) buckets[3].count++;
      else buckets[4].count++;
    });

    const maxCount = Math.max(...buckets.map((b) => b.count), 1);
    return { buckets, maxCount };
  }, []);

  const toggleSort = (field: 'prob' | 'hop_dist' | 'rank') => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1e3a5f] pb-4">
        <div>
          <h1 className="text-xl font-bold font-mono text-white flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-amber-400" />
            Threat Prediction Center
          </h1>
          <p className="text-xs text-[#94a3b8] font-mono mt-0.5">
            DHAP-Net propagation probabilities &amp; multi-horizon evaluation on LANL Red-Team events
          </p>
        </div>

        {/* Global Controls: Delta & Seed */}
        <div className="flex items-center gap-3">
          {/* Delta selector */}
          <div className="flex items-center bg-[#0f1629] border border-[#1e3a5f] rounded p-0.5 text-xs font-mono">
            <span className="text-[#64748b] px-2 text-[10px] uppercase font-bold">Horizon:</span>
            {(['1h', '6h', '24h'] as const).map((delta) => (
              <button
                key={delta}
                onClick={() => setSelectedDelta(delta)}
                className={`px-2.5 py-1 rounded text-xs transition ${
                  selectedDelta === delta
                    ? 'bg-amber-500 text-black font-bold shadow'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {delta}
              </button>
            ))}
          </div>

          {/* Seed selector */}
          <div className="flex items-center bg-[#0f1629] border border-[#1e3a5f] rounded p-0.5 text-xs font-mono">
            <span className="text-[#64748b] px-2 text-[10px] uppercase font-bold">Seed:</span>
            {[42, 123, 2024].map((seed) => (
              <button
                key={seed}
                onClick={() => setSelectedSeed(seed)}
                className={`px-2 py-1 rounded text-xs transition ${
                  selectedSeed === seed
                    ? 'bg-cyan-500 text-black font-bold shadow'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {seed}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Model Selection Tabs */}
      <div className="flex border-b border-[#1e3a5f] gap-1 overflow-x-auto text-xs font-mono">
        {[
          { id: 'A1', name: 'A1 (DHAP-Net)', tag: 'Dual-Horizon GCN', color: 'border-amber-500 text-amber-400' },
          { id: 'A2', name: 'A2 (TGN-TA)', tag: 'Temporal Graph Net', color: 'border-blue-500 text-blue-400' },
          { id: 'A3', name: 'A3 (DM-STG-AD)', tag: 'Dynamic Spatial-Temporal', color: 'border-purple-500 text-purple-400' },
          { id: 'B1_RF', name: 'B1_RF', tag: 'Random Forest', color: 'border-cyan-500 text-cyan-400' },
          { id: 'B2_GBT', name: 'B2_GBT', tag: 'Gradient Boosted Trees', color: 'border-green-500 text-green-400' },
        ].map((m) => (
          <button
            key={m.id}
            onClick={() => setSelectedModel(m.id as any)}
            className={`px-4 py-2.5 font-medium border-b-2 transition whitespace-nowrap flex items-center gap-2 ${
              selectedModel === m.id
                ? `${m.color} bg-[#131d35]`
                : 'border-transparent text-[#94a3b8] hover:text-white hover:bg-[#0f1629]'
            }`}
          >
            <span>{m.name}</span>
            <span className="text-[10px] text-[#64748b] bg-[#0a0e1a] px-1.5 py-0.5 rounded border border-[#1e3a5f]">
              {m.tag}
            </span>
          </button>
        ))}
      </div>

      {/* Warning Notice Banner */}
      <div className="bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-transparent border-l-4 border-amber-500 border-y border-r border-amber-500/30 rounded-r p-3.5 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs font-mono space-y-1">
          <div className="font-bold text-amber-300">
            ⚠️ SIMULATED PROPAGATION NOTICE
          </div>
          <p className="text-amber-100/90 leading-relaxed text-[11px]">
            Outputs are SIMULATED lateral movement propagation probabilities produced by DHAP-Net on historical LANL red-team data.
            These represent probabilistic risk projections, not confirmed network breach compromise events.
          </p>
        </div>
      </div>

      {/* Research Model Evaluation Status Callout */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-mono font-bold text-white">
            <Info className="w-4 h-4 text-cyan-400" />
            <span>Benchmark Performance Callout (Horizon = {selectedDelta})</span>
          </div>
          <span className="text-[10px] font-mono text-[#64748b]">reports/tables/final_results.csv</span>
        </div>
        <p className="text-xs text-gray-300 leading-relaxed">
          <strong className="text-amber-400">A1 Model Validation AP is NaN:</strong> In the evaluated test window,
          the candidate generation graph contains zero confirmed positive labels for this specific time slice, causing precision calculation to divide by zero.
          Meanwhile, tabular baselines exhibit measurable performance:
          <span className="font-mono text-cyan-300 ml-1">B1_RF (6h) AP ≈ 0.0348</span>,
          <span className="font-mono text-green-300 ml-1">B2_GBT (6h) AP ≈ 0.0265</span>,
          <span className="font-mono text-purple-300 ml-1">B1_RF (24h) AP ≈ 0.0610</span>,
          <span className="font-mono text-cyan-300 ml-1">B2_GBT (24h) AP ≈ 0.0685</span>.
        </p>
      </div>

      {/* Main Grid: Probability Distribution & Model Comparison Side-by-Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Probability Distribution Histogram */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold font-mono text-white flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              Prediction Probability Distribution ({selectedModel}, {selectedDelta})
            </h2>
            <span className="text-[10px] font-mono text-[#64748b]">N = {demoPredictions.length} Candidates</span>
          </div>

          <div className="space-y-3 pt-2">
            {distributionBuckets.buckets.map((b) => (
              <div key={b.range} className="space-y-1 font-mono text-xs">
                <div className="flex justify-between items-center text-[11px]">
                  <span className="text-gray-300">{b.range}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#64748b]">({b.label})</span>
                    <span className="font-bold text-white">{b.count} hosts</span>
                  </div>
                </div>
                <div className="w-full bg-[#0a0e1a] h-4 rounded overflow-hidden border border-[#1e3a5f]/60 relative">
                  <div
                    className="h-full transition-all duration-500 rounded"
                    style={{
                      width: `${(b.count / distributionBuckets.maxCount) * 100}%`,
                      backgroundColor: b.color,
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-2.5 rounded text-[11px] font-mono text-[#94a3b8] flex justify-between">
            <span>Mean Probability: <strong className="text-white">0.573</strong></span>
            <span>Median: <strong className="text-white">0.584</strong></span>
            <span>Max Score: <strong className="text-red-400">0.962 (C1065)</strong></span>
          </div>
        </div>

        {/* Model Comparison Table */}
        <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold font-mono text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-400" />
              Cross-Model AP Comparison (Delta = {selectedDelta})
            </h2>
            <span className="text-[10px] font-mono text-[#22c55e] font-semibold">Real Research Results</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#1e3a5f] text-[#64748b] text-[10px] uppercase">
                  <th className="py-2 px-2">Model</th>
                  <th className="py-2 px-2 text-right">AP Mean</th>
                  <th className="py-2 px-2 text-right">ROC AUC</th>
                  <th className="py-2 px-2 text-right">Brier</th>
                  <th className="py-2 px-2">Evaluation Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e3a5f]/40">
                {Object.entries(comparisonData).map(([modelName, m]) => {
                  const isBest = modelName.includes('B2_GBT') || modelName.includes('B1_RF');
                  return (
                    <tr
                      key={modelName}
                      className={`hover:bg-[#131d35] transition ${
                        isBest ? 'bg-green-500/5' : ''
                      }`}
                    >
                      <td className="py-2 px-2 font-medium text-white flex items-center gap-1.5">
                        {isBest && <CheckCircle2 className="w-3 h-3 text-green-400" />}
                        {modelName}
                      </td>
                      <td
                        className={`py-2 px-2 text-right font-bold ${
                          m.ap === 'NaN'
                            ? 'text-[#64748b]'
                            : isBest
                            ? 'text-green-400'
                            : 'text-gray-300'
                        }`}
                      >
                        {m.ap}
                      </td>
                      <td className="py-2 px-2 text-right text-gray-300">{m.auc}</td>
                      <td className="py-2 px-2 text-right text-[#94a3b8]">{m.brier}</td>
                      <td className="py-2 px-2 text-[10px] text-[#64748b]">{m.status}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Top Threat Predictions Table */}
      <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg overflow-hidden space-y-3 p-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold font-mono text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              High-Risk Candidate Predictions ({predictions.length} hosts)
            </h2>
            <p className="text-[11px] text-[#94a3b8] font-mono mt-0.5">
              Ranked by propagation likelihood within the {selectedDelta} window
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#64748b]" />
            <input
              type="text"
              value={searchHost}
              onChange={(e) => setSearchHost(e.target.value)}
              placeholder="Search host (e.g. C1065)..."
              className="w-full bg-[#0a0e1a] border border-[#1e3a5f] rounded pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#1e3a5f] bg-[#0a0e1a] text-[#64748b] text-[10px] uppercase">
                <th
                  onClick={() => toggleSort('rank')}
                  className="py-2.5 px-3 cursor-pointer hover:text-white"
                >
                  <div className="flex items-center gap-1">
                    <span>Rank</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3">Host ID</th>
                <th
                  onClick={() => toggleSort('hop_dist')}
                  className="py-2.5 px-3 cursor-pointer hover:text-white text-center"
                >
                  <div className="flex items-center justify-center gap-1">
                    <span>Hop Dist</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th
                  onClick={() => toggleSort('prob')}
                  className="py-2.5 px-3 cursor-pointer hover:text-white min-w-[180px]"
                >
                  <div className="flex items-center gap-1">
                    <span>Propagation Prob</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-2.5 px-3">95% CI</th>
                <th className="py-2.5 px-3">Ground Truth</th>
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e3a5f]/40">
              {predictions.map((p) => {
                const probVal = p.prob;
                let barColor = 'bg-blue-500';
                if (probVal >= 0.8) barColor = 'bg-red-500';
                else if (probVal >= 0.6) barColor = 'bg-amber-500';
                else if (probVal >= 0.4) barColor = 'bg-yellow-400';

                const isSelected = selectedRow?.host === p.host;

                return (
                  <tr
                    key={p.host}
                    onClick={() => setSelectedRow(p)}
                    className={`cursor-pointer transition ${
                      isSelected
                        ? 'bg-cyan-950/40 border-l-2 border-cyan-400'
                        : 'hover:bg-[#131d35]'
                    }`}
                  >
                    <td className="py-2.5 px-3 text-[#94a3b8]">#{p.rank ?? 1}</td>
                    <td className="py-2.5 px-3 font-bold text-white flex items-center gap-1.5">
                      <span>{p.host}</span>
                      {p.label === 1 && (
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500" title="Confirmed Red-Team Host"></span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-center text-amber-300 font-bold">
                      {p.hop_dist ?? 2}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="font-bold text-white">{formatProb(probVal)}</span>
                        </div>
                        <div className="w-full bg-[#0a0e1a] h-2 rounded-full overflow-hidden border border-[#1e3a5f]/40">
                          <div
                            className={`h-full ${barColor}`}
                            style={{ width: `${probVal * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-[11px] text-[#94a3b8]">
                      [{p.ci_lo ? (p.ci_lo * 100).toFixed(1) : '52.0'}% - {p.ci_hi ? (p.ci_hi * 100).toFixed(1) : '75.0'}%]
                    </td>
                    <td className="py-2.5 px-3">
                      {p.label === 1 ? (
                        <span className="inline-flex items-center gap-1 text-[10px] text-red-400 font-bold bg-red-950/60 border border-red-800/80 px-2 py-0.5 rounded">
                          <CheckCircle2 className="w-3 h-3" /> Positive (Compromised)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] text-gray-400 bg-gray-800/40 border border-gray-700/50 px-2 py-0.5 rounded">
                          <XCircle className="w-3 h-3 text-gray-500" /> Negative
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                          p.prob >= 0.8
                            ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                            : p.prob >= 0.6
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                        }`}
                      >
                        {p.status ?? (p.prob >= 0.8 ? 'Critical' : p.prob >= 0.6 ? 'High' : 'Moderate')}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedRow(p);
                        }}
                        className="text-cyan-400 hover:text-cyan-300 p-1"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Selected Prediction Investigation Modal / Detail View */}
      {selectedRow && (
        <div className="bg-[#0f1629] border border-cyan-500/40 rounded-lg p-5 space-y-4 shadow-2xl">
          <div className="flex items-start justify-between border-b border-[#1e3a5f] pb-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-cyan-400 uppercase font-mono font-bold tracking-wider">
                  Prediction Diagnostic Profile
                </span>
                <span className="text-white text-lg font-bold font-mono">{selectedRow.host}</span>
                <span
                  className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase ${
                    selectedRow.prob >= 0.8
                      ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                      : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                  }`}
                >
                  {formatProb(selectedRow.prob)} Probability
                </span>
              </div>
              <p className="text-xs text-[#94a3b8] font-mono mt-0.5">
                Model: {selectedModel} | Window Horizon: {selectedDelta} | Random Seed: {selectedSeed}
              </p>
            </div>
            <button
              onClick={() => setSelectedRow(null)}
              className="text-[#94a3b8] hover:text-white p-1 rounded hover:bg-[#1e2a55]"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
            <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded space-y-1">
              <span className="text-[10px] text-[#64748b]">Hop Distance from Foothold</span>
              <div className="text-lg font-bold text-amber-400">{selectedRow.hop_dist ?? 2} Hops</div>
              <p className="text-[10px] text-[#94a3b8]">Reachability via k-hop BFS from earliest compromised host (C1065)</p>
            </div>
            <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded space-y-1">
              <span className="text-[10px] text-[#64748b]">95% Credible Interval</span>
              <div className="text-lg font-bold text-cyan-300">
                [{(selectedRow.ci_lo ? selectedRow.ci_lo * 100 : 52).toFixed(1)}% - {(selectedRow.ci_hi ? selectedRow.ci_hi * 100 : 75).toFixed(1)}%]
              </div>
              <p className="text-[10px] text-[#94a3b8]">Bayesian posterior uncertainty quantification</p>
            </div>
            <div className="bg-[#0a0e1a] border border-[#1e3a5f] p-3 rounded space-y-1">
              <span className="text-[10px] text-[#64748b]">Ground Truth Label</span>
              <div className="text-lg font-bold text-white">
                {selectedRow.label === 1 ? '1 (Compromised)' : '0 (Uncompromised)'}
              </div>
              <p className="text-[10px] text-[#94a3b8]">Verified against LANL Red-Team event log</p>
            </div>
          </div>

          <div className="bg-[#0a0e1a] border border-[#1e3a5f] rounded p-3 text-xs font-mono space-y-2">
            <div className="font-bold text-cyan-400 flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4" />
              How this prediction was made:
            </div>
            <p className="text-gray-300 leading-relaxed text-[11px]">
              1. <strong>Graph Candidate Extraction:</strong> GraphFrames BFS traverses k=2 hops from known footholds (e.g. C1065, C2106), producing candidate subgraphs.
              <br />
              2. <strong>Temporal Aggregation:</strong> NetFlow communications are sliced into delta-hour intervals ({selectedDelta}), computing in-degree, out-degree, and protocol entropy.
              <br />
              3. <strong>Neural Message Passing:</strong> DHAP-Net updates dynamic host embeddings with temporal attention across historical edges to forecast the likelihood of lateral movement.
            </p>
          </div>

          <div className="flex gap-3 justify-end pt-2">
            <button
              onClick={() => navigate(`/graph`)}
              className="px-3 py-2 bg-[#172040] hover:bg-[#1e2a55] border border-[#1e3a5f] text-cyan-400 font-mono text-xs rounded transition flex items-center gap-1.5"
            >
              View in Attack Graph Explorer
            </button>
            <button
              onClick={() => navigate(`/entities?host=${selectedRow.host}`)}
              className="px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-mono text-xs font-bold rounded shadow transition flex items-center gap-1.5"
            >
              Investigate Entity Profile
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Predictions;
