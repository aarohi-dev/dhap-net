import type {
  SystemStatus,
  FlowEvent,
  AttackGraph,
  Prediction,
  AnomalyEvent,
  Host,
  Edge,
  ModelMetrics,
} from '../types';

// ─── Demo Hosts ───────────────────────────────────────────────────────────────

const LANL_HOSTS = [
  'C1065','C2106','C17693','C3799','C5971',
  'C8551','C10101','C12861','C14238','C15692',
  'C22932','C24987','C1118','C4931','C9204',
  'U620','U724','U1131','C101','C6003',
];

// ─── System Status (Demo — all offline) ───────────────────────────────────────

export const demoSystemStatus: SystemStatus = {
  demo_mode: true,
  pipeline_active: false,
  last_updated: new Date().toISOString(),
  kafka: {
    status: 'offline',
    broker: 'localhost:9092',
    topic: 'netflow-events',
    events_per_sec: 0,
    lag: 0,
  },
  spark: {
    status: 'offline',
    master: 'spark://localhost:7077',
    active_jobs: 0,
    workers: 0,
    ms_per_batch: 0,
  },
  neo4j: {
    status: 'offline',
    bolt_url: 'bolt://localhost:7687',
    node_count: 0,
    relationship_count: 0,
  },
};

// ─── Flow Events ──────────────────────────────────────────────────────────────

export const demoFlowEvents: FlowEvent[] = [
  { id:'f1',  time:1388534400, duration:0.12, src:'C1065',  dst:'C2106',  src_port:49152, dst_port:445,  protocol:6,  packets:12, bytes_val:8192  },
  { id:'f2',  time:1388534460, duration:0.05, src:'C2106',  dst:'C17693', src_port:52001, dst_port:139,  protocol:6,  packets:6,  bytes_val:2048  },
  { id:'f3',  time:1388534520, duration:0.30, src:'C3799',  dst:'C5971',  src_port:50000, dst_port:443,  protocol:6,  packets:28, bytes_val:51200 },
  { id:'f4',  time:1388534580, duration:0.02, src:'U620',   dst:'C1065',  src_port:1024,  dst_port:22,   protocol:6,  packets:4,  bytes_val:512   },
  { id:'f5',  time:1388534640, duration:0.80, src:'C8551',  dst:'C10101', src_port:49200, dst_port:80,   protocol:6,  packets:55, bytes_val:98304 },
  { id:'f6',  time:1388534700, duration:0.01, src:'C17693', dst:'C1118',  src_port:53200, dst_port:53,   protocol:17, packets:2,  bytes_val:128   },
  { id:'f7',  time:1388534760, duration:0.40, src:'C12861', dst:'C14238', src_port:49300, dst_port:3389, protocol:6,  packets:35, bytes_val:65536 },
  { id:'f8',  time:1388534820, duration:0.07, src:'C15692', dst:'C22932', src_port:60000, dst_port:135,  protocol:6,  packets:8,  bytes_val:1024  },
  { id:'f9',  time:1388534880, duration:0.15, src:'C24987', dst:'C3799',  src_port:49400, dst_port:445,  protocol:6,  packets:14, bytes_val:16384 },
  { id:'f10', time:1388534940, duration:0.03, src:'C4931',  dst:'C9204',  src_port:50500, dst_port:443,  protocol:6,  packets:5,  bytes_val:768   },
  { id:'f11', time:1388535000, duration:0.60, src:'C1065',  dst:'C15692', src_port:49600, dst_port:445,  protocol:6,  packets:48, bytes_val:81920 },
  { id:'f12', time:1388535060, duration:0.11, src:'C5971',  dst:'C8551',  src_port:49700, dst_port:139,  protocol:6,  packets:10, bytes_val:3072  },
  { id:'f13', time:1388535120, duration:0.22, src:'C10101', dst:'C12861', src_port:60100, dst_port:445,  protocol:6,  packets:20, bytes_val:32768 },
  { id:'f14', time:1388535180, duration:0.09, src:'U724',   dst:'C17693', src_port:1025,  dst_port:22,   protocol:6,  packets:7,  bytes_val:896   },
  { id:'f15', time:1388535240, duration:0.45, src:'C101',   dst:'C6003',  src_port:49800, dst_port:3389, protocol:6,  packets:38, bytes_val:73728 },
];

// ─── Attack Graph ─────────────────────────────────────────────────────────────

const graphNodes: Host[] = [
  // 5 Confirmed Compromised nodes (Red)
  { id:'C1065',  label:'C1065',  type:'compromised', risk_score:0.96, in_degree:14, out_degree:18, bytes_in:524288, hop_dist:0, n_comp_nb:4, n_flows_w:65, protocol_entropy:0.65 },
  { id:'C2106',  label:'C2106',  type:'compromised', risk_score:0.91, in_degree:10, out_degree:12, bytes_in:262144, hop_dist:1, n_comp_nb:3, n_flows_w:42, protocol_entropy:0.58 },
  { id:'C12861', label:'C12861', type:'compromised', risk_score:0.88, in_degree:9,  out_degree:11, bytes_in:314572, hop_dist:1, n_comp_nb:3, n_flows_w:38, protocol_entropy:0.62 },
  { id:'C5250',  label:'C5250',  type:'compromised', risk_score:0.85, in_degree:7,  out_degree:8,  bytes_in:198200, hop_dist:1, n_comp_nb:2, n_flows_w:29, protocol_entropy:0.51 },
  { id:'C19932', label:'C19932', type:'compromised', risk_score:0.82, in_degree:6,  out_degree:7,  bytes_in:175400, hop_dist:1, n_comp_nb:2, n_flows_w:25, protocol_entropy:0.49 },

  // 7 Predicted Risk nodes (Amber, varying probabilities)
  { id:'C17693', label:'C17693', type:'predicted',   risk_score:0.87, in_degree:8,  out_degree:9,  bytes_in:131072, hop_dist:2, n_comp_nb:2, n_flows_w:31, protocol_entropy:0.72 },
  { id:'C8551',  label:'C8551',  type:'predicted',   risk_score:0.78, in_degree:6,  out_degree:8,  bytes_in:98304,  hop_dist:2, n_comp_nb:1, n_flows_w:24, protocol_entropy:0.55 },
  { id:'C14238', label:'C14238', type:'predicted',   risk_score:0.69, in_degree:5,  out_degree:7,  bytes_in:73728,  hop_dist:2, n_comp_nb:1, n_flows_w:19, protocol_entropy:0.48 },
  { id:'C18824', label:'C18824', type:'predicted',   risk_score:0.63, in_degree:4,  out_degree:6,  bytes_in:61440,  hop_dist:3, n_comp_nb:1, n_flows_w:16, protocol_entropy:0.44 },
  { id:'C22585', label:'C22585', type:'predicted',   risk_score:0.58, in_degree:5,  out_degree:5,  bytes_in:51200,  hop_dist:2, n_comp_nb:1, n_flows_w:14, protocol_entropy:0.42 },
  { id:'C1118',  label:'C1118',  type:'predicted',   risk_score:0.49, in_degree:4,  out_degree:4,  bytes_in:32768,  hop_dist:3, n_comp_nb:1, n_flows_w:11, protocol_entropy:0.39 },
  { id:'C4931',  label:'C4931',  type:'predicted',   risk_score:0.42, in_degree:3,  out_degree:4,  bytes_in:28672,  hop_dist:3, n_comp_nb:0, n_flows_w:9,  protocol_entropy:0.35 },

  // Normal nodes (Blue)
  { id:'C3799',  label:'C3799',  type:'normal',      risk_score:0.15, in_degree:2,  out_degree:3,  bytes_in:16384,  hop_dist:4, n_comp_nb:0, n_flows_w:8,  protocol_entropy:0.30 },
  { id:'C5971',  label:'C5971',  type:'normal',      risk_score:0.22, in_degree:3,  out_degree:4,  bytes_in:24576,  hop_dist:4, n_comp_nb:0, n_flows_w:12, protocol_entropy:0.41 },
  { id:'C10101', label:'C10101', type:'normal',      risk_score:0.10, in_degree:2,  out_degree:2,  bytes_in:8192,   hop_dist:5, n_comp_nb:0, n_flows_w:5,  protocol_entropy:0.20 },
  { id:'C15692', label:'C15692', type:'normal',      risk_score:0.18, in_degree:2,  out_degree:3,  bytes_in:12288,  hop_dist:4, n_comp_nb:0, n_flows_w:7,  protocol_entropy:0.25 },
  { id:'C24987', label:'C24987', type:'normal',      risk_score:0.12, in_degree:2,  out_degree:4,  bytes_in:10240,  hop_dist:5, n_comp_nb:0, n_flows_w:6,  protocol_entropy:0.28 },
  { id:'C9204',  label:'C9204',  type:'normal',      risk_score:0.09, in_degree:2,  out_degree:2,  bytes_in:7168,   hop_dist:5, n_comp_nb:0, n_flows_w:4,  protocol_entropy:0.19 },

  // Server nodes (Hubs)
  { id:'C22932', label:'C22932', type:'server',      risk_score:0.05, in_degree:24, out_degree:6,  bytes_in:2097152,hop_dist:6, n_comp_nb:0, n_flows_w:90, protocol_entropy:0.85 },
  { id:'C101',   label:'C101',   type:'server',      risk_score:0.08, in_degree:18, out_degree:4,  bytes_in:1048576,hop_dist:5, n_comp_nb:0, n_flows_w:72, protocol_entropy:0.79 },

  // User workstations
  { id:'U620',   label:'U620',   type:'user',        risk_score:0.35, in_degree:1,  out_degree:6,  bytes_in:4096,   hop_dist:3, n_comp_nb:0, n_flows_w:14, protocol_entropy:0.40 },
  { id:'U724',   label:'U724',   type:'user',        risk_score:0.28, in_degree:1,  out_degree:5,  bytes_in:3072,   hop_dist:4, n_comp_nb:0, n_flows_w:10, protocol_entropy:0.35 },
];

const graphEdges: Edge[] = [
  // Compromised attack propagation (Red, confirmed)
  { id:'e1',  source:'C1065',  target:'C2106',  relationship:'COMPROMISED',           weight:0.95, n_flows:58, total_bytes:624288, protocol:6  },
  { id:'e2',  source:'C1065',  target:'C12861', relationship:'COMPROMISED',           weight:0.91, n_flows:46, total_bytes:494912, protocol:6  },
  { id:'e3',  source:'C2106',  target:'C5250',  relationship:'COMPROMISED',           weight:0.86, n_flows:32, total_bytes:314572, protocol:6  },
  { id:'e4',  source:'C12861', target:'C19932', relationship:'COMPROMISED',           weight:0.83, n_flows:28, total_bytes:245760, protocol:6  },

  // Simulated propagation edges (Amber, dashed/model predicted)
  { id:'e5',  source:'C2106',  target:'C17693', relationship:'SIMULATED_PROPAGATION', weight:0.87, n_flows:24, total_bytes:151072, protocol:6  },
  { id:'e6',  source:'C17693', target:'C8551',  relationship:'SIMULATED_PROPAGATION', weight:0.78, n_flows:19, total_bytes:98304,  protocol:6  },
  { id:'e7',  source:'C12861', target:'C14238', relationship:'SIMULATED_PROPAGATION', weight:0.69, n_flows:16, total_bytes:81920,  protocol:6  },
  { id:'e8',  source:'C14238', target:'C18824', relationship:'SIMULATED_PROPAGATION', weight:0.63, n_flows:12, total_bytes:61440,  protocol:6  },
  { id:'e9',  source:'C5250',  target:'C22585', relationship:'SIMULATED_PROPAGATION', weight:0.58, n_flows:14, total_bytes:55296,  protocol:6  },
  { id:'e10', source:'C22585', target:'C1118',  relationship:'SIMULATED_PROPAGATION', weight:0.49, n_flows:9,  total_bytes:32768,  protocol:6  },
  { id:'e11', source:'C19932', target:'C4931',  relationship:'SIMULATED_PROPAGATION', weight:0.42, n_flows:8,  total_bytes:24576,  protocol:6  },
  { id:'e12', source:'C8551',  target:'C3799',  relationship:'SIMULATED_PROPAGATION', weight:0.38, n_flows:7,  total_bytes:18432,  protocol:6  },

  // Communications (Grey, observed network flows)
  { id:'e13', source:'C1065',  target:'C15692', relationship:'COMMUNICATES_WITH',     weight:0.45, n_flows:18, total_bytes:98304,  protocol:6  },
  { id:'e14', source:'C3799',  target:'C5971',  relationship:'COMMUNICATES_WITH',     weight:0.20, n_flows:8,  total_bytes:24576,  protocol:6  },
  { id:'e15', source:'U620',   target:'C1065',  relationship:'COMMUNICATES_WITH',     weight:0.35, n_flows:10, total_bytes:4096,   protocol:6  },
  { id:'e16', source:'C8551',  target:'C10101', relationship:'COMMUNICATES_WITH',     weight:0.30, n_flows:12, total_bytes:49152,  protocol:6  },
  { id:'e17', source:'C22932', target:'C1065',  relationship:'COMMUNICATES_WITH',     weight:0.10, n_flows:60, total_bytes:1048576,protocol:6  },
  { id:'e18', source:'C24987', target:'C3799',  relationship:'COMMUNICATES_WITH',     weight:0.15, n_flows:6,  total_bytes:16384,  protocol:6  },
  { id:'e19', source:'U724',   target:'C17693', relationship:'COMMUNICATES_WITH',     weight:0.28, n_flows:8,  total_bytes:3072,   protocol:6  },
  { id:'e20', source:'C101',   target:'C22932', relationship:'COMMUNICATES_WITH',     weight:0.05, n_flows:50, total_bytes:819200, protocol:6  },
  { id:'e21', source:'C5971',  target:'C8551',  relationship:'COMMUNICATES_WITH',     weight:0.22, n_flows:10, total_bytes:32768,  protocol:6  },
  { id:'e22', source:'C10101', target:'C12861', relationship:'COMMUNICATES_WITH',     weight:0.40, n_flows:14, total_bytes:57344,  protocol:6  },
  { id:'e23', source:'C12861', target:'C2106',  relationship:'COMMUNICATES_WITH',     weight:0.60, n_flows:22, total_bytes:163840, protocol:6  },
  { id:'e24', source:'C15692', target:'C22932', relationship:'COMMUNICATES_WITH',     weight:0.08, n_flows:7,  total_bytes:12288,  protocol:17 },
  { id:'e25', source:'C4931',  target:'C9204',  relationship:'COMMUNICATES_WITH',     weight:0.12, n_flows:5,  total_bytes:768,    protocol:6  },
  { id:'e26', source:'C9204',  target:'C22932', relationship:'COMMUNICATES_WITH',     weight:0.11, n_flows:6,  total_bytes:4096,   protocol:6  },
  { id:'e27', source:'C1118',  target:'C101',   relationship:'COMMUNICATES_WITH',     weight:0.15, n_flows:9,  total_bytes:8192,   protocol:17 },
  { id:'e28', source:'C18824', target:'C22932', relationship:'COMMUNICATES_WITH',     weight:0.18, n_flows:11, total_bytes:16384,  protocol:6  },
  { id:'e29', source:'C22585', target:'C101',   relationship:'COMMUNICATES_WITH',     weight:0.14, n_flows:8,  total_bytes:12288,  protocol:6  },
  { id:'e30', source:'U620',   target:'C2106',  relationship:'COMMUNICATES_WITH',     weight:0.25, n_flows:7,  total_bytes:5120,   protocol:6  },
  { id:'e31', source:'U724',   target:'C5250',  relationship:'COMMUNICATES_WITH',     weight:0.21, n_flows:6,  total_bytes:4608,   protocol:6  },
  { id:'e32', source:'C3799',  target:'C22932', relationship:'COMMUNICATES_WITH',     weight:0.09, n_flows:5,  total_bytes:7168,   protocol:6  },
  { id:'e33', source:'C5971',  target:'C101',   relationship:'COMMUNICATES_WITH',     weight:0.08, n_flows:4,  total_bytes:5120,   protocol:6  },
  { id:'e34', source:'C1065',  target:'C101',   relationship:'COMMUNICATES_WITH',     weight:0.32, n_flows:15, total_bytes:45056,  protocol:6  },
  { id:'e35', source:'C2106',  target:'C22932', relationship:'COMMUNICATES_WITH',     weight:0.28, n_flows:13, total_bytes:38912,  protocol:6  },
];

export const demoAttackGraph: AttackGraph = {
  nodes: graphNodes,
  edges: graphEdges,
  metadata: {
    timestamp: new Date().toISOString(),
    total_nodes: graphNodes.length,
    total_edges: graphEdges.length,
  },
};

// ─── Predictions ─────────────────────────────────────────────────────────────

export const demoPredictions: Prediction[] = [
  { host:'C1065',  prob:0.9624, label:1, delta:'6h', model:'A1', seed:42, rank:1,  hop_dist:0, ci_lo:0.932, ci_hi:0.985, status:'Confirmed' },
  { host:'C2106',  prob:0.9145, label:1, delta:'6h', model:'A1', seed:42, rank:2,  hop_dist:1, ci_lo:0.871, ci_hi:0.948, status:'Confirmed' },
  { host:'C12861', prob:0.8834, label:1, delta:'6h', model:'A1', seed:42, rank:3,  hop_dist:1, ci_lo:0.842, ci_hi:0.920, status:'Confirmed' },
  { host:'C17693', prob:0.8731, label:1, delta:'6h', model:'A1', seed:42, rank:4,  hop_dist:2, ci_lo:0.825, ci_hi:0.912, status:'Critical' },
  { host:'C8551',  prob:0.7819, label:0, delta:'6h', model:'A1', seed:42, rank:5,  hop_dist:2, ci_lo:0.718, ci_hi:0.835, status:'High' },
  { host:'C14238', prob:0.6942, label:0, delta:'6h', model:'A1', seed:42, rank:6,  hop_dist:2, ci_lo:0.628, ci_hi:0.754, status:'High' },
  { host:'C18824', prob:0.6315, label:0, delta:'6h', model:'A1', seed:42, rank:7,  hop_dist:3, ci_lo:0.560, ci_hi:0.698, status:'Medium' },
  { host:'C22585', prob:0.5840, label:0, delta:'6h', model:'A1', seed:42, rank:8,  hop_dist:2, ci_lo:0.510, ci_hi:0.652, status:'Medium' },
  { host:'C1118',  prob:0.4921, label:0, delta:'6h', model:'A1', seed:42, rank:9,  hop_dist:3, ci_lo:0.420, ci_hi:0.561, status:'Medium' },
  { host:'C4931',  prob:0.4215, label:0, delta:'6h', model:'A1', seed:42, rank:10, hop_dist:3, ci_lo:0.350, ci_hi:0.489, status:'Low' },
  { host:'U620',   prob:0.3521, label:0, delta:'6h', model:'A1', seed:42, rank:11, hop_dist:3, ci_lo:0.280, ci_hi:0.420, status:'Low' },
  { host:'C5971',  prob:0.2140, label:0, delta:'6h', model:'A1', seed:42, rank:12, hop_dist:4, ci_lo:0.150, ci_hi:0.275, status:'Low' },
  { host:'C3799',  prob:0.1483, label:0, delta:'6h', model:'A1', seed:42, rank:13, hop_dist:4, ci_lo:0.090, ci_hi:0.205, status:'Low' },
  { host:'C10101', prob:0.1025, label:0, delta:'6h', model:'A1', seed:42, rank:14, hop_dist:5, ci_lo:0.055, ci_hi:0.150, status:'Low' },
  { host:'C22932', prob:0.0523, label:0, delta:'6h', model:'A1', seed:42, rank:15, hop_dist:6, ci_lo:0.020, ci_hi:0.085, status:'Low' },
];

// ─── Anomaly Events ───────────────────────────────────────────────────────────

export const demoAnomalies: AnomalyEvent[] = [
  {
    id:'a1', host:'C1065',  timestamp:'2014-01-01T02:15:00Z', score:0.95,
    type:'lateral_movement', severity:'critical', acknowledged:false,
    description:'Unusual SMB traffic pattern detected — 12 new host connections in 6h window',
  },
  {
    id:'a2', host:'C12861', timestamp:'2014-01-01T03:42:00Z', score:0.88,
    type:'lateral_movement', severity:'critical', acknowledged:false,
    description:'RDP connections to 7 hosts outside normal communication profile',
  },
  {
    id:'a3', host:'C2106',  timestamp:'2014-01-01T04:08:00Z', score:0.82,
    type:'c2_comm', severity:'high', acknowledged:false,
    description:'Periodic beaconing pattern detected on port 443 — 5-min intervals',
  },
  {
    id:'a4', host:'C17693', timestamp:'2014-01-01T05:30:00Z', score:0.74,
    type:'scanning', severity:'high', acknowledged:false,
    description:'Port scan activity — 139/445 probes across /24 subnet',
  },
  {
    id:'a5', host:'C8551',  timestamp:'2014-01-01T06:11:00Z', score:0.65,
    type:'privilege_esc', severity:'high', acknowledged:true,
    description:'Elevated privilege authentication events from non-admin account',
  },
  {
    id:'a6', host:'U620',   timestamp:'2014-01-01T07:45:00Z', score:0.52,
    type:'exfiltration', severity:'medium', acknowledged:true,
    description:'Anomalous outbound data volume — 3x baseline over 2h period',
  },
  {
    id:'a7', host:'C14238', timestamp:'2014-01-01T09:22:00Z', score:0.44,
    type:'scanning', severity:'medium', acknowledged:false,
    description:'DNS query volume spike — 500% above baseline',
  },
  {
    id:'a8', host:'C5971',  timestamp:'2014-01-01T11:00:00Z', score:0.31,
    type:'c2_comm', severity:'low', acknowledged:true,
    description:'Low-frequency irregular connection to known C2 IP range',
  },
];

// ─── Model Metrics (from final_results.csv) ───────────────────────────────────

export const demoModelMetrics: ModelMetrics[] = [
  // A1 — DHAP-Net (our model)
  { model:'A1', delta_h:6,  AP_mean:0.2847, AP_std:0.0231, ROC_AUC_mean:0.8912, ROC_AUC_std:0.0145 },
  { model:'A1', delta_h:1,  AP_mean:0.1923, AP_std:0.0318, ROC_AUC_mean:0.8541, ROC_AUC_std:0.0188 },
  { model:'A1', delta_h:24, AP_mean:0.3214, AP_std:0.0197, ROC_AUC_mean:0.9103, ROC_AUC_std:0.0122 },
  // A2 — TGN-TA
  { model:'A2', delta_h:6,  AP_mean:0.2234, AP_std:0.0287, ROC_AUC_mean:0.8674, ROC_AUC_std:0.0163 },
  { model:'A2', delta_h:1,  AP_mean:0.1612, AP_std:0.0345, ROC_AUC_mean:0.8323, ROC_AUC_std:0.0201 },
  { model:'A2', delta_h:24, AP_mean:0.2591, AP_std:0.0254, ROC_AUC_mean:0.8887, ROC_AUC_std:0.0138 },
  // A3 — DM-STG-AD
  { model:'A3', delta_h:6,  AP_mean:0.1987, AP_std:0.0312, ROC_AUC_mean:0.8412, ROC_AUC_std:0.0177 },
  { model:'A3', delta_h:1,  AP_mean:0.1445, AP_std:0.0398, ROC_AUC_mean:0.8102, ROC_AUC_std:0.0215 },
  { model:'A3', delta_h:24, AP_mean:0.2318, AP_std:0.0279, ROC_AUC_mean:0.8756, ROC_AUC_std:0.0151 },
  // Baselines — delta 6h
  { model:'B1_RF',         delta_h:6,  AP_mean:0.0351, AP_std:0.0089, ROC_AUC_mean:0.6821, ROC_AUC_std:0.0312 },
  { model:'B2_GBT',        delta_h:6,  AP_mean:0.0264, AP_std:0.0074, ROC_AUC_mean:0.6512, ROC_AUC_std:0.0287 },
  { model:'B3_LR',         delta_h:6,  AP_mean:0.0198, AP_std:0.0062, ROC_AUC_mean:0.6234, ROC_AUC_std:0.0315 },
  { model:'B4_FixedDiff',  delta_h:6,  AP_mean:0.0423, AP_std:0.0091, ROC_AUC_mean:0.6945, ROC_AUC_std:0.0298 },
  { model:'B5_NearestHop', delta_h:6,  AP_mean:0.0315, AP_std:0.0078, ROC_AUC_mean:0.6678, ROC_AUC_std:0.0304 },
  { model:'B5_Random',     delta_h:6,  AP_mean:0.0089, AP_std:0.0031, ROC_AUC_mean:0.5000, ROC_AUC_std:0.0000 },
];

export { LANL_HOSTS };
