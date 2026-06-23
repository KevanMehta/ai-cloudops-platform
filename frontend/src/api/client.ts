import type {
  AgentRun,
  Anomaly,
  CloudCost,
  CostTrendPoint,
  DashboardData,
  HealthStatus,
  KubernetesWorkload,
  Recommendation,
  ServiceBreakdown,
  TerraformFinding,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API error ${response.status}: ${text}`);
  }
  return response.json();
}

export const api = {
  health: () => fetchApi<HealthStatus>('/health'),
  dashboard: () => fetchApi<DashboardData>('/api/dashboard'),
  costs: (days = 90) =>
    fetchApi<{ costs: CloudCost[]; total: number; by_service: ServiceBreakdown[]; trend: CostTrendPoint[] }>(
      `/api/costs?days=${days}`,
    ),
  anomalies: () =>
    fetchApi<{ anomalies: Anomaly[]; count_by_severity: Record<string, number> }>('/api/anomalies'),
  recommendations: () =>
    fetchApi<{ recommendations: Recommendation[]; total_estimated_savings: number }>(
      '/api/recommendations',
    ),
  kubernetes: () =>
    fetchApi<{
      workloads: KubernetesWorkload[];
      unhealthy_count: number;
      cluster_summary: Record<string, number | string>;
    }>('/api/kubernetes'),
  runAgent: () =>
    fetchApi<AgentRun>('/api/agent/run', {
      method: 'POST',
      body: JSON.stringify({ include_terraform: true, include_kubernetes: true }),
    }),
  analyzeTerraform: (filePath?: string) =>
    fetchApi<{ findings: TerraformFinding[]; files_analyzed: string[]; risk_score: number }>(
      '/api/terraform/analyze',
      { method: 'POST', body: JSON.stringify({ file_path: filePath ?? null }) },
    ),
};

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

export function parseActionSteps(steps: string): string[] {
  try {
    return JSON.parse(steps);
  } catch {
    return [steps];
  }
}
