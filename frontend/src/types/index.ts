export interface ServiceBreakdown {
  service: string;
  total: number;
  percentage: number;
}

export interface CostTrendPoint {
  date: string;
  amount: number;
}

export interface Recommendation {
  id: number;
  title: string;
  category: string;
  severity: string;
  estimated_monthly_savings: number;
  explanation: string;
  action_steps: string;
  source: string;
  created_at: string;
}

export interface DashboardData {
  total_monthly_spend: number;
  projected_spend: number;
  anomaly_count: number;
  top_expensive_services: ServiceBreakdown[];
  cost_trend: CostTrendPoint[];
  service_breakdown: ServiceBreakdown[];
  optimization_recommendations: Recommendation[];
}

export interface CloudCost {
  id: number;
  date: string;
  service: string;
  amount: number;
  region: string;
  account_id: string;
}

export interface Anomaly {
  id: number;
  detected_at: string;
  service: string;
  date: string;
  amount: number;
  expected_amount: number;
  deviation_percent: number;
  severity: string;
  explanation: string;
  resolved: boolean;
}

export interface AgentRun {
  id: number;
  started_at: string;
  completed_at: string | null;
  status: string;
  steps_completed: string;
  cost_analysis: string | null;
  anomaly_summary: string | null;
  infra_inspection: string | null;
  recommendations_summary: string | null;
  executive_summary: string | null;
  used_openai: boolean;
}

export interface TerraformFinding {
  id: number;
  file_name: string;
  resource_type: string;
  resource_name: string;
  issue_type: string;
  severity: string;
  description: string;
  recommendation: string;
  analyzed_at: string;
}

export interface KubernetesWorkload {
  id: number;
  namespace: string;
  name: string;
  workload_type: string;
  replicas: number;
  ready_replicas: number;
  cpu_usage_percent: number;
  memory_usage_percent: number;
  restart_count: number;
  status: string;
  health: string;
  recommendation: string | null;
}

export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  redis: string;
}
