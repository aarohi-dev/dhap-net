import client, { isDemoMode } from './client';
import type {
  SystemStatus,
  FlowEvent,
  AttackGraph,
  Prediction,
  AnomalyEvent,
  EntityProfile,
  ModelMetrics,
  ApiResponse,
} from '../types';
import {
  demoSystemStatus,
  demoFlowEvents,
  demoAttackGraph,
  demoPredictions,
  demoAnomalies,
  demoModelMetrics,
} from '../data/fixtures';

// ─── Helper ───────────────────────────────────────────────────────────────────

async function tryFetch<T>(
  apiFn: () => Promise<T>,
  fallback: T,
): Promise<T> {
  if (isDemoMode()) return fallback;
  try {
    return await apiFn();
  } catch {
    return fallback;
  }
}

// ─── API Functions ────────────────────────────────────────────────────────────

export async function getSystemStatus(): Promise<SystemStatus> {
  return tryFetch(
    async () => {
      const { data } = await client.get<SystemStatus>('/api/status');
      return data;
    },
    demoSystemStatus,
  );
}

export interface FlowParams {
  limit?: number;
  src?: string;
  dst?: string;
  protocol?: number;
  since?: number;
}

export async function getFlowEvents(params: FlowParams = {}): Promise<FlowEvent[]> {
  return tryFetch(
    async () => {
      const { data } = await client.get<FlowEvent[]>('/api/flows', { params });
      return data;
    },
    demoFlowEvents,
  );
}

export async function getAttackGraph(limit = 500): Promise<AttackGraph> {
  return tryFetch(
    async () => {
      const { data } = await client.get<AttackGraph>('/api/graph', { params: { limit } });
      return data;
    },
    demoAttackGraph,
  );
}

export async function getPredictions(
  model = 'A1',
  delta = '6h',
  seed = 42,
): Promise<Prediction[]> {
  return tryFetch(
    async () => {
      const { data } = await client.get<Prediction[]>('/api/predictions', {
        params: { model, delta, seed },
      });
      return data;
    },
    demoPredictions,
  );
}

export interface AnomalyParams {
  limit?: number;
  severity?: string;
  acknowledged?: boolean;
}

export async function getAnomalies(params: AnomalyParams = {}): Promise<AnomalyEvent[]> {
  return tryFetch(
    async () => {
      const { data } = await client.get<AnomalyEvent[]>('/api/anomalies', { params });
      return data;
    },
    demoAnomalies,
  );
}

export async function getEntityProfile(hostId: string): Promise<EntityProfile> {
  return tryFetch(
    async () => {
      const { data } = await client.get<EntityProfile>(`/api/entities/${hostId}`);
      return data;
    },
    {
      host: demoAttackGraph.nodes.find((n) => n.id === hostId) ?? demoAttackGraph.nodes[0],
      recent_flows: demoFlowEvents.filter(
        (f) => f.src === hostId || f.dst === hostId,
      ).slice(0, 5),
      anomalies: demoAnomalies.filter((a) => a.host === hostId).slice(0, 3),
      predictions: demoPredictions.filter((p) => p.host === hostId),
      connected_hosts: [
        ...new Set(
          demoFlowEvents
            .filter((f) => f.src === hostId || f.dst === hostId)
            .map((f) => (f.src === hostId ? f.dst : f.src)),
        ),
      ].slice(0, 10),
      timeline: [],
    } as EntityProfile,
  );
}

export async function getModelMetrics(): Promise<ModelMetrics[]> {
  return tryFetch(
    async () => {
      const { data } = await client.get<ModelMetrics[]>('/api/metrics');
      return data;
    },
    demoModelMetrics,
  );
}

export async function getRedteamEvents(): Promise<unknown[]> {
  return tryFetch(
    async () => {
      const { data } = await client.get<unknown[]>('/api/redteam');
      return data;
    },
    [],
  );
}

export async function getSliceWindow(): Promise<unknown> {
  return tryFetch(
    async () => {
      const { data } = await client.get('/api/slice-window');
      return data;
    },
    {
      t_first_redteam: 1388534400,
      t_last_redteam: 1389139200,
      t_start: 1388448000,
      t_end: 1389225600,
      rt_events_covered: 749,
      rt_events_total: 749,
    },
  );
}

export async function getThroughput(): Promise<unknown> {
  return tryFetch(
    async () => {
      const { data } = await client.get('/api/throughput');
      return data;
    },
    {
      events_per_sec: 0,
      ms_per_batch: 0,
      total_batches: 0,
      elapsed_s: 0,
    },
  );
}

// Re-export ApiResponse type for convenience
export type { ApiResponse };
