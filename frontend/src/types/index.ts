// ─── System Status ───────────────────────────────────────────────────────────

export interface KafkaStatus {
  status: 'online' | 'offline' | 'degraded';
  broker: string;
  topic?: string;
  events_per_sec?: number;
  lag?: number;
}

export interface SparkStatus {
  status: 'online' | 'offline' | 'degraded';
  master: string;
  active_jobs?: number;
  workers?: number;
  ms_per_batch?: number;
}

export interface Neo4jStatus {
  status: 'online' | 'offline' | 'degraded';
  bolt_url: string;
  node_count?: number;
  relationship_count?: number;
}

export interface SystemStatus {
  demo_mode: boolean;
  kafka: KafkaStatus;
  spark: SparkStatus;
  neo4j: Neo4jStatus;
  pipeline_active: boolean;
  last_updated: string;
}

// ─── Network Flow ─────────────────────────────────────────────────────────────

export interface FlowEvent {
  id: string;
  time: number;        // unix epoch seconds
  duration: number;    // seconds
  src: string;         // e.g. "C1065"
  dst: string;         // e.g. "C2106"
  src_port: number;
  dst_port: number;
  protocol: number;    // 6=TCP, 17=UDP, 1=ICMP
  packets: number;
  bytes_val: number;
}

// ─── Graph ────────────────────────────────────────────────────────────────────

export type HostType = 'normal' | 'compromised' | 'predicted' | 'server' | 'user';

export interface Host {
  id: string;           // e.g. "C1065"
  label: string;
  type: HostType;
  risk_score: number;   // 0-1
  in_degree: number;
  out_degree: number;
  bytes_in: number;
  hop_dist?: number;
  n_comp_nb?: number;
  n_flows_w?: number;
  protocol_entropy?: number;
  ip?: string;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  relationship: 'COMMUNICATES_WITH' | 'COMPROMISED' | 'SIMULATED_PROPAGATION';
  weight: number;
  n_flows?: number;
  total_bytes?: number;
  protocol?: number;
}

export interface AttackGraph {
  nodes: Host[];
  edges: Edge[];
  metadata?: {
    timestamp: string;
    total_nodes: number;
    total_edges: number;
  };
}

export interface AttackPath {
  path: string[];       // sequence of host IDs
  risk_score: number;
  length: number;
}

// ─── Predictions ──────────────────────────────────────────────────────────────

export interface Prediction {
  host: string;
  prob: number;         // 0-1 from model
  label: number;        // 0 or 1 ground truth
  delta: string;        // "1h" | "6h" | "24h"
  model: string;        // "A1" | "A2" | "A3"
  seed: number;
  rank?: number;
  hop_dist?: number;
  ci_lo?: number;
  ci_hi?: number;
  status?: string;
}

export interface AnomalyEvent {
  id: string;
  host: string;
  timestamp: string;    // ISO
  score: number;        // 0-1
  type: 'lateral_movement' | 'exfiltration' | 'scanning' | 'c2_comm' | 'privilege_esc';
  description: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  acknowledged: boolean;
}

export interface EntityProfile {
  host: Host;
  recent_flows: FlowEvent[];
  anomalies: AnomalyEvent[];
  predictions: Prediction[];
  connected_hosts: string[];
  timeline: {
    time: string;
    event: string;
    severity: string;
  }[];
}

// ─── Model Metrics ────────────────────────────────────────────────────────────

export interface ModelMetrics {
  model: string;        // "A1" | "A2" | ... | "B1_RF" etc.
  delta_h: number;      // 1 | 6 | 24
  AP_mean: number;
  AP_std: number;
  ROC_AUC_mean: number;
  ROC_AUC_std?: number;
  F1_mean?: number;
  P_mean?: number;
  R_mean?: number;
}

export interface TrainingResult {
  epoch: number;
  loss: number;
  val_loss: number;
  ap: number;
  val_ap: number;
}

export interface ComparisonRow {
  model: string;
  delta_h: number;
  AP_mean: number;
  AP_std: number;
  ROC_AUC_mean: number;
  ROC_AUC_std: number;
  rank?: number;
}

// ─── Candidates ───────────────────────────────────────────────────────────────

export interface Candidate {
  host: string;
  delta: string;        // "1h" | "6h" | "24h"
  label: number;        // ground truth
  hop_dist: number;
  in_degree: number;
  out_degree: number;
  bytes_in: number;
  n_comp_nb: number;
  n_flows_w: number;
  protocol_entropy: number;
  prob?: number;        // prediction probability
}

// ─── Shared ───────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: string;
  timestamp: string;
  demo_mode: boolean;
}

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'none';
