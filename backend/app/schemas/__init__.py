from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CloudCostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    service: str
    amount: float
    region: str
    account_id: str


class AnomalyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    detected_at: datetime
    service: str
    date: date
    amount: float
    expected_amount: float
    deviation_percent: float
    severity: str
    explanation: str
    resolved: bool


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    severity: str
    estimated_monthly_savings: float
    explanation: str
    action_steps: str
    source: str
    created_at: datetime


class AgentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    completed_at: Optional[datetime]
    status: str
    steps_completed: str
    cost_analysis: Optional[str]
    anomaly_summary: Optional[str]
    infra_inspection: Optional[str]
    recommendations_summary: Optional[str]
    executive_summary: Optional[str]
    used_openai: bool


class TerraformFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    resource_type: str
    resource_name: str
    issue_type: str
    severity: str
    description: str
    recommendation: str
    analyzed_at: datetime


class KubernetesWorkloadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    namespace: str
    name: str
    workload_type: str
    replicas: int
    ready_replicas: int
    cpu_usage_percent: float
    memory_usage_percent: float
    restart_count: int
    status: str
    health: str
    recommendation: Optional[str]


class ServiceBreakdown(BaseModel):
    service: str
    total: float
    percentage: float


class CostTrendPoint(BaseModel):
    date: date
    amount: float


class DashboardResponse(BaseModel):
    total_monthly_spend: float
    projected_spend: float
    anomaly_count: int
    top_expensive_services: list[ServiceBreakdown]
    cost_trend: list[CostTrendPoint]
    service_breakdown: list[ServiceBreakdown]
    optimization_recommendations: list[RecommendationOut]


class CostsResponse(BaseModel):
    costs: list[CloudCostOut]
    total: float
    by_service: list[ServiceBreakdown]
    trend: list[CostTrendPoint]


class AnomaliesResponse(BaseModel):
    anomalies: list[AnomalyOut]
    count_by_severity: dict[str, int]


class RecommendationsResponse(BaseModel):
    recommendations: list[RecommendationOut]
    total_estimated_savings: float


class KubernetesResponse(BaseModel):
    workloads: list[KubernetesWorkloadOut]
    unhealthy_count: int
    cluster_summary: dict[str, int | float]


class TerraformAnalyzeRequest(BaseModel):
    file_path: Optional[str] = Field(
        default=None, description="Specific file to analyze; defaults to all samples"
    )


class TerraformAnalyzeResponse(BaseModel):
    findings: list[TerraformFindingOut]
    files_analyzed: list[str]
    risk_score: int


class AgentRunRequest(BaseModel):
    include_terraform: bool = True
    include_kubernetes: bool = True


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis: str
