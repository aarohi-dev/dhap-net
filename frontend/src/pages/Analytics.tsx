import React, { useState, useMemo } from 'react';
import {
  BarChart3, TrendingUp, Activity, Zap, Info,
  ExternalLink, AlertTriangle, Database, Clock, Shield
} from 'lucide-react';
import { demoModelMetrics, demoPredictions, demoAttackGraph } from '@/data/fixtures';
import { formatProb } from '@/lib/utils';
import type { ModelMetrics } from '@/types';

// ── Stat card ────────────────────────────────────────────────────────────────
const StatCard: React.FC<{
  icon: React.ReactNode; value: string; label: string; sub?: string; color?: string;
}> = ({ icon, value, label, sub, color = 'text-cyan-400' }) => (
  <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4">
    <div className="text-blue-400/70 mb-3">{icon}</div>
    <div className={`text-2xl font-mono font-bold ${color}`}>{value}</div>
    <div className="text-xs text-[#94a3b8] mt-1">{label}</div>
    {sub && <div className="text-[11px] text-[#64748b] mt-0.5 font-mono">{sub}</div>}
  </div>
);

// ── Simple bar chart (CSS) ───────────────────────────────────────────────────
const BarChartSimple: React.FC<{
  data: { label: string; value: number; color?: string }[];
  maxValue?: number;
  valueFormat?: (v: number) => string;
}> = ({ data, maxValue: mV, valueFormat = v => v.toFixed(4) }) => {
  const max = mV ?? Math.max(...data.map(d => d.value), 0.001);
  return (
    <div className="space-y-2">
      {data.map(d => (
        <div key={d.label} className="flex items-center gap-3">
          <div className="w-28 text-xs font-mono text-[#94a3b8] text-right shrink-0 truncate">{d.label}</div>
          <div className="flex-1 h-5 bg-[#1e3a5f]/40 rounded overflow-hidden">
            <div
              className="h-full rounded transition-all duration-500"
              style={{
                width: `${Math.max((d.value / max) * 100, 1)}%`,
                background: d.color ?? '#3b82f6',
              }}
            />
          </div>
          <div className="w-16 text-xs font-mono text-white text-right shrink-0">{valueFormat(d.value)}</div>
        </div>
      ))}
    </div>
  );
};

// ── Training loss chart (CSS) ────────────────────────────────────────────────
const TrainingLossChart: React.FC = () => {
  const seeds = [
    { seed: 42, losses: [248.3, 153.5, 600.9, 147.5, 292.6, 580.7], color: '#3b82f6' },
    { seed: 123, losses: [1531.5, 963.1, 196.5, 300.0, 844.9, 787.6], color: '#06b6d4' },
    { seed: 2024, losses: [4085.2, 2210.7, 5086.1, 4769.5, 1308.5, 1515.6], color: '#8b5cf6' },
  ];
  const maxLoss = Math.max(...seeds.flatMap(s => s.losses));

  return (
    <div>
      <div className="flex items-center gap-4 mb-4">
        {seeds.map(s => (
          <div key={s.seed} className="flex items-center gap-1.5 text-xs font-mono text-[#94a3b8]">
            <span className="w-3 h-0.5 rounded" style={{ background: s.color }} />
            Seed {s.seed}
          </div>
        ))}
      </div>
      <div className="space-y-3">
        {[0, 1, 2, 3, 4, 5].map(epoch => (
          <div key={epoch}>
            <div className="text-[10px] text-[#64748b] font-mono mb-1">Epoch {epoch}</div>
            <div className="flex gap-1">
              {seeds.map(s => (
                <div key={s.seed} className="flex-1 h-4 bg-[#1e3a5f]/30 rounded overflow-hidden">
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${(s.losses[epoch] / maxLoss) * 100}%`,
                      background: s.color,
                      opacity: 0.8,
                    }}
                  />
                </div>
              ))}
            </div>
            <div className="flex gap-1 mt-0.5">
              {seeds.map(s => (
                <div key={s.seed} className="flex-1 text-[9px] font-mono text-[#64748b] text-center">
                  {s.losses[epoch].toFixed(0)}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// ── Visualization card ───────────────────────────────────────────────────────
const VizCard: React.FC<{
  title: string; filename: string; description: string;
}> = ({ title, filename, description }) => (
  <a
    href={`/visualizations/${filename}`}
    target="_blank"
    rel="noopener noreferrer"
    className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-4 hover:border-[#3b82f6]/50 transition-colors group block"
  >
    <div className="flex items-start justify-between mb-2">
      <div className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors">{title}</div>
      <ExternalLink className="w-3.5 h-3.5 text-[#64748b] group-hover:text-blue-400 transition-colors shrink-0 mt-0.5" />
    </div>
    <div className="text-xs text-[#64748b]">{description}</div>
    <div className="mt-2 text-[10px] font-mono text-[#475569]">{filename}</div>
  </a>
);

// ── Main Analytics page ──────────────────────────────────────────────────────
const TABS = ['Overview', 'Model Performance', 'Training History', 'Throughput', 'Coverage', 'Visualizations'] as const;
type Tab = typeof TABS[number];

const Analytics: React.FC = () => {
  const [tab, setTab] = useState<Tab>('Overview');

  const delta6Metrics = demoModelMetrics.filter(m => m.delta_h === 6);
  const allModelsGrouped = useMemo(() => {
    const map = new Map<string, ModelMetrics[]>();
    demoModelMetrics.forEach(m => {
      const arr = map.get(m.model) || [];
      arr.push(m);
      map.set(m.model, arr);
    });
    return map;
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-lg font-bold text-white font-mono flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-400" /> Research Analytics & Insights
        </h1>
        <p className="text-xs text-[#64748b] mt-1">
          Model performance metrics, training history, and pipeline analytics from the DHAP-Net research implementation.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#0a0e1a] border border-[#1e3a5f] rounded-lg p-1 overflow-x-auto">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded text-xs font-mono transition-colors whitespace-nowrap ${
              tab === t
                ? 'bg-[#1a2a4a] text-white border border-[#3b82f6]/40'
                : 'text-[#64748b] hover:text-[#94a3b8] hover:bg-[#0f1629]'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === 'Overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard icon={<Activity className="w-4 h-4" />} value="130.4M" label="Total Network Events" sub="LANL netflow dataset" />
            <StatCard icon={<Database className="w-4 h-4" />} value={String(demoAttackGraph.nodes.length)} label="Graph Nodes" sub="Host entities" color="text-blue-400" />
            <StatCard icon={<AlertTriangle className="w-4 h-4" />} value="749" label="Red-Team Events" sub="Confirmed compromises" color="text-red-400" />
            <StatCard icon={<Clock className="w-4 h-4" />} value="15 days" label="Analysis Window" sub="t_start=0, t_end=1,296,000s" color="text-purple-400" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <StatCard icon={<Zap className="w-4 h-4" />} value="243,126" label="Events/sec (Replay)" sub="200 batches, 0.5ms/batch" />
            <StatCard icon={<Shield className="w-4 h-4" />} value="3 models" label="DHAP-Net Architecture Variants" sub="A1, A2, A3 + 5 baselines" color="text-cyan-400" />
            <StatCard icon={<TrendingUp className="w-4 h-4" />} value="9 checkpoints" label="Trained Models" sub="3 deltas × 3 seeds" color="text-amber-400" />
          </div>

          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-xs text-amber-200">
            <div className="font-semibold text-amber-400 mb-1 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5" /> Research Status Note
            </div>
            <p>
              The A1 model (DHAP-Net) validation AP is <span className="font-mono text-amber-400">NaN</span> — the test partition 
              contains insufficient positive labels in the current 15-day time slice (663 of 749 red-team events covered). 
              Baselines B1_RF and B2_GBT show measurable but modest AP (0.035–0.069 at 6h–24h horizons). 
              Coverage ceiling analysis shows 0% k-hop reachability from earliest footholds, suggesting 
              sparse graph connectivity limits the graph-based candidate generation approach.
            </p>
          </div>
        </div>
      )}

      {tab === 'Model Performance' && (
        <div className="space-y-6">
          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
            <h3 className="text-sm font-semibold text-white mb-1">Average Precision (AP) — Δ = 6h</h3>
            <p className="text-xs text-[#64748b] mb-4">Higher is better. All models evaluated on LANL test set.</p>
            <BarChartSimple
              data={delta6Metrics.map(m => ({
                label: m.model,
                value: m.AP_mean,
                color: m.model.startsWith('A') ? '#06b6d4' : m.model.startsWith('B5') ? '#6b7280' : '#3b82f6',
              }))}
            />
          </div>

          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
            <h3 className="text-sm font-semibold text-white mb-1">ROC-AUC — Δ = 6h</h3>
            <p className="text-xs text-[#64748b] mb-4">Area under the receiver operating characteristic curve.</p>
            <BarChartSimple
              data={delta6Metrics.map(m => ({
                label: m.model,
                value: m.ROC_AUC_mean,
                color: m.model.startsWith('A') ? '#06b6d4' : '#3b82f6',
              }))}
              maxValue={1.0}
            />
          </div>

          {/* Full results table */}
          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-[#1e3a5f]">
              <h3 className="text-sm font-semibold text-white">Full Model Comparison</h3>
              <p className="text-xs text-[#64748b]">All models across all prediction horizons (Δ = 1h, 6h, 24h)</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-[#1e3a5f] text-[#64748b]">
                    <th className="px-3 py-2.5 text-left font-mono">Model</th>
                    <th className="px-3 py-2.5 text-center font-mono">Δ</th>
                    <th className="px-3 py-2.5 text-right font-mono">AP Mean</th>
                    <th className="px-3 py-2.5 text-right font-mono">AP Std</th>
                    <th className="px-3 py-2.5 text-right font-mono">ROC-AUC</th>
                  </tr>
                </thead>
                <tbody>
                  {demoModelMetrics.map((m, i) => (
                    <tr key={`${m.model}-${m.delta_h}-${i}`}
                      className="border-b border-[#1e3a5f]/50 hover:bg-[#1a2a4a]/40 transition-colors">
                      <td className="px-3 py-2 font-mono font-semibold text-blue-300">{m.model}</td>
                      <td className="px-3 py-2 text-center font-mono text-[#94a3b8]">{m.delta_h}h</td>
                      <td className="px-3 py-2 text-right font-mono text-white">{m.AP_mean.toFixed(4)}</td>
                      <td className="px-3 py-2 text-right font-mono text-[#64748b]">±{m.AP_std.toFixed(4)}</td>
                      <td className="px-3 py-2 text-right font-mono text-cyan-300">{m.ROC_AUC_mean.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-4 py-2.5 border-t border-[#1e3a5f] text-[10px] text-[#64748b] font-mono">
              Source: reports/tables/final_results.csv · Metrics averaged over seeds (42, 123, 2024)
            </div>
          </div>
        </div>
      )}

      {tab === 'Training History' && (
        <div className="space-y-6">
          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
            <h3 className="text-sm font-semibold text-white mb-1">A1 (DHAP-Net) Training Loss — Δ = 6h</h3>
            <p className="text-xs text-[#64748b] mb-4">
              BCE loss per epoch across 3 random seeds. Early stopping at epoch 5 (patience=3). 
              Validation AP remained NaN due to zero positive labels in validation partition.
            </p>
            <TrainingLossChart />
          </div>

          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
            <h3 className="text-sm font-semibold text-white mb-2">Training Wall Time</h3>
            <div className="grid grid-cols-3 gap-4">
              {[
                { seed: 42, time: '6m 39s', timeS: 399 },
                { seed: 123, time: '6m 55s', timeS: 415 },
                { seed: 2024, time: '12h 26m', timeS: 44783 },
              ].map(({ seed, time, timeS }) => (
                <div key={seed} className="bg-[#1a2a4a] rounded p-3">
                  <div className="text-[10px] text-[#64748b] font-mono">Seed {seed}</div>
                  <div className="text-lg font-mono font-bold text-white mt-1">{time}</div>
                  <div className="text-[10px] text-[#64748b] font-mono mt-0.5">{timeS.toLocaleString()}s</div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-[#64748b]">
              Note: Seed 2024 took 12+ hours due to full dataset iteration. Seeds 42 and 123 terminated via early stopping.
            </div>
          </div>
        </div>
      )}

      {tab === 'Throughput' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
              <div className="text-4xl font-mono font-bold text-cyan-400">243,126</div>
              <div className="text-xs text-[#94a3b8] mt-2">Events processed per second</div>
              <div className="text-[10px] text-[#64748b] font-mono mt-1">Historical replay speed (Kafka producer → Spark)</div>
            </div>
            <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
              <div className="text-4xl font-mono font-bold text-blue-400">0.50 ms</div>
              <div className="text-xs text-[#94a3b8] mt-2">Average micro-batch latency</div>
              <div className="text-[10px] text-[#64748b] font-mono mt-1">Spark Structured Streaming processing time</div>
            </div>
            <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
              <div className="text-4xl font-mono font-bold text-purple-400">200</div>
              <div className="text-xs text-[#94a3b8] mt-2">Total micro-batches</div>
              <div className="text-[10px] text-[#64748b] font-mono mt-1">100ms elapsed total processing time</div>
            </div>
          </div>

          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-xs text-amber-200">
            <div className="font-semibold text-amber-400 mb-1">Historical Replay Note</div>
            These throughput numbers represent the Kafka→Spark historical replay speed, not a live production benchmark. 
            The pipeline replays flows.txt (130M records, 942 MB) at maximum speed to populate the graph and run inference.
          </div>
        </div>
      )}

      {tab === 'Coverage' && (
        <div className="space-y-6">
          <div className="bg-[#0f1629] border border-[#1e3a5f] rounded-lg p-5">
            <h3 className="text-sm font-semibold text-white mb-1">k-Hop Coverage Ceiling</h3>
            <p className="text-xs text-[#64748b] mb-4">
              Fraction of future-compromised hosts reachable from the earliest-known compromised footholds via k-hop BFS 
              on the communication graph.
            </p>
            <div className="space-y-3">
              {[
                { k: 1, coverage: 0.0, label: '1-hop' },
                { k: 2, coverage: 0.0, label: '2-hop' },
                { k: 3, coverage: 0.0, label: '3-hop' },
              ].map(({ k, coverage, label }) => (
                <div key={k} className="flex items-center gap-3">
                  <div className="w-16 text-xs font-mono text-[#94a3b8] text-right">{label}</div>
                  <div className="flex-1 h-6 bg-[#1e3a5f]/40 rounded overflow-hidden relative">
                    <div
                      className="h-full rounded bg-red-500/60"
                      style={{ width: `${Math.max(coverage * 100, 2)}%` }}
                    />
                    <span className="absolute inset-y-0 left-2 flex items-center text-xs font-mono text-white">
                      {(coverage * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-xs text-red-200">
            <div className="font-semibold text-red-400 mb-1 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" /> Coverage Analysis Result
            </div>
            <p className="mb-2">
              The coverage ceiling is <span className="font-mono font-semibold text-red-400">0.0%</span> at all hop distances (k=1,2,3).
            </p>
            <p>
              <strong>Interpretation:</strong> The earliest-known compromised footholds (≈20% of compromised hosts by time) have 
              <em>no communication graph edges</em> connecting them to the remaining future-compromised hosts within the 15-day 
              analysis window. This means the graph-based k-hop BFS candidate generation — the foundation of DHAP-Net's 
              attack propagation model — cannot discover future victims from known seeds in this dataset configuration.
            </p>
            <p className="mt-2">
              <strong>Possible causes:</strong> The LANL anonymised host naming may create disconnected graph components; 
              the 15-day time slice may be too narrow; or the red-team activity may follow non-network paths not captured in netflow.
            </p>
            <p className="mt-2 text-[#64748b]">
              Source: reports/coverage_ceiling.json · Computed by pipeline/05_graphframes_candidates.py
            </p>
          </div>
        </div>
      )}

      {tab === 'Visualizations' && (
        <div className="space-y-4">
          <p className="text-xs text-[#64748b]">
            Pre-rendered Plotly interactive visualizations from the DHAP-Net research pipeline. Click to open in a new tab.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <VizCard title="Dataset Statistics" filename="01_dataset_stats.html" description="Flow count, host distribution, temporal coverage" />
            <VizCard title="Red-Team Timeline" filename="02_redteam_timeline.html" description="Confirmed compromise events over time" />
            <VizCard title="Traffic & Degree Distribution" filename="03_traffic_and_degree_dist.html" description="Host in/out-degree and traffic volume distributions" />
            <VizCard title="Coverage Ceiling" filename="04_coverage_ceiling.html" description="k-hop reachability from compromised footholds" />
            <VizCard title="PR Curves (Δ=1h)" filename="05_pr_curves_delta1h.html" description="Precision-recall curves for 1-hour prediction horizon" />
            <VizCard title="PR Curves (Δ=6h)" filename="06_pr_curves_delta6h.html" description="Precision-recall curves for 6-hour prediction horizon" />
            <VizCard title="PR Curves (Δ=24h)" filename="07_pr_curves_delta24h.html" description="Precision-recall curves for 24-hour prediction horizon" />
            <VizCard title="Reliability Diagram" filename="08_reliability_diagram.html" description="Calibration of predicted probabilities" />
            <VizCard title="Fan Chart — Credible Intervals" filename="09_fan_chart_credible_intervals.html" description="Prediction uncertainty visualization" />
            <VizCard title="Ablation Study" filename="10_ablation_study.html" description="Component contribution analysis" />
            <VizCard title="Model Comparison" filename="11_model_comparison.html" description="Head-to-head model performance comparison" />
            <VizCard title="Streaming Throughput" filename="12_streaming_throughput.html" description="Kafka→Spark processing throughput over time" />
            <VizCard title="Attack Graph (Interactive)" filename="13_attack_graph_interactive.html" description="Plotly-based interactive attack propagation graph" />
            <VizCard title="Time Slider Animation" filename="14_time_slider_animation.html" description="Temporal evolution of the attack graph" />
            <VizCard title="Neo4j Bloom View" filename="15_neo4j_bloom_view.html" description="Neo4j Bloom graph visualization export" />
          </div>
        </div>
      )}
    </div>
  );
};

export default Analytics;
