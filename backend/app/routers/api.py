import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.agent.workflow import run_agent_workflow
from app.config import settings
from app.database import get_db
from app.schemas import (
    AgentRunOut,
    AgentRunRequest,
    AnomaliesResponse,
    AnomalyOut,
    CloudCostOut,
    CostsResponse,
    DashboardResponse,
    HealthResponse,
    KubernetesResponse,
    KubernetesWorkloadOut,
    RecommendationOut,
    RecommendationsResponse,
    TerraformAnalyzeRequest,
    TerraformAnalyzeResponse,
    TerraformFindingOut,
)
from app.services.anomaly_detection import get_all_anomalies
from app.services.cache import cache_get, cache_set, check_redis_health
from app.services.dashboard import get_costs, get_dashboard
from app.services.kubernetes_monitor import get_all_workloads, get_kubernetes_summary
from app.services.recommendations import generate_recommendations, get_all_recommendations
from app.services.terraform_analyzer import analyze_terraform, calculate_risk_score

logger = logging.getLogger(__name__)

router = APIRouter()

REQUEST_COUNT = Counter(
    "cloudops_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "cloudops_http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"],
)


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.app_version,
        database=db_status,
        redis=check_redis_health(),
    )


@router.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)):
    cached = cache_get("dashboard")
    if cached:
        return DashboardResponse(**cached)

    start = time.time()
    data = get_dashboard(db)
    REQUEST_LATENCY.labels(endpoint="dashboard").observe(time.time() - start)
    REQUEST_COUNT.labels(method="GET", endpoint="dashboard", status="200").inc()

    cache_set("dashboard", data.model_dump())
    return data


@router.get("/api/costs", response_model=CostsResponse)
def costs(days: int = 90, db: Session = Depends(get_db)):
    cost_rows, total, by_service, trend = get_costs(db, days=days)
    return CostsResponse(
        costs=[CloudCostOut.model_validate(c) for c in cost_rows[:500]],
        total=total,
        by_service=by_service,
        trend=trend,
    )


@router.get("/api/anomalies", response_model=AnomaliesResponse)
def anomalies(db: Session = Depends(get_db)):
    items = get_all_anomalies(db)
    count_by_severity: dict[str, int] = {}
    for a in items:
        count_by_severity[a.severity] = count_by_severity.get(a.severity, 0) + 1
    return AnomaliesResponse(
        anomalies=[AnomalyOut.model_validate(a) for a in items],
        count_by_severity=count_by_severity,
    )


@router.get("/api/recommendations", response_model=RecommendationsResponse)
def recommendations(db: Session = Depends(get_db)):
    items = get_all_recommendations(db)
    total_savings = sum(r.estimated_monthly_savings for r in items)
    return RecommendationsResponse(
        recommendations=[RecommendationOut.model_validate(r) for r in items],
        total_estimated_savings=round(total_savings, 2),
    )


@router.get("/api/kubernetes", response_model=KubernetesResponse)
def kubernetes(db: Session = Depends(get_db)):
    workloads = get_all_workloads(db)
    summary = get_kubernetes_summary(db)
    return KubernetesResponse(
        workloads=[KubernetesWorkloadOut.model_validate(w) for w in workloads],
        unhealthy_count=summary["unhealthy_count"],
        cluster_summary=summary,
    )


@router.post("/api/agent/run", response_model=AgentRunOut)
def run_agent(body: AgentRunRequest, db: Session = Depends(get_db)):
    run = run_agent_workflow(
        db,
        include_terraform=body.include_terraform,
        include_kubernetes=body.include_kubernetes,
    )
    cache_set("dashboard", get_dashboard(db).model_dump())
    return AgentRunOut.model_validate(run)


@router.post("/api/terraform/analyze", response_model=TerraformAnalyzeResponse)
def terraform_analyze(body: TerraformAnalyzeRequest, db: Session = Depends(get_db)):
    findings, files = analyze_terraform(db, file_path=body.file_path, persist=True)
    generate_recommendations(db)
    return TerraformAnalyzeResponse(
        findings=[TerraformFindingOut.model_validate(f) for f in findings],
        files_analyzed=files,
        risk_score=calculate_risk_score(findings),
    )
