"""LangGraph-style agent workflow for CloudOps analysis."""

import json
import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AgentRun
from app.services.anomaly_detection import detect_anomalies, get_all_anomalies
from app.services.dashboard import get_dashboard
from app.services.kubernetes_monitor import get_all_workloads, get_kubernetes_summary
from app.services.recommendations import generate_recommendations, get_all_recommendations
from app.services.terraform_analyzer import analyze_terraform

logger = logging.getLogger(__name__)


class AgentState:
    def __init__(self):
        self.cost_analysis: str = ""
        self.anomaly_summary: str = ""
        self.infra_inspection: str = ""
        self.recommendations_summary: str = ""
        self.executive_summary: str = ""
        self.steps_completed: list[str] = []


def step_analyze_costs(db: Session, state: AgentState) -> AgentState:
    dashboard = get_dashboard(db)
    state.cost_analysis = (
        f"Total monthly spend: ${dashboard.total_monthly_spend:,.2f}. "
        f"Projected end-of-month: ${dashboard.projected_spend:,.2f}. "
        f"Top services: {', '.join(f'{s.service} (${s.total:,.0f})' for s in dashboard.top_expensive_services[:3])}."
    )
    state.steps_completed.append("analyze_cost_data")
    return state


def step_detect_anomalies(db: Session, state: AgentState) -> AgentState:
    detect_anomalies(db)
    anomalies = get_all_anomalies(db)
    by_severity: dict[str, int] = {}
    for a in anomalies:
        by_severity[a.severity] = by_severity.get(a.severity, 0) + 1
    state.anomaly_summary = (
        f"Found {len(anomalies)} anomalies. "
        f"Severity breakdown: {json.dumps(by_severity)}. "
        + (
            f"Most recent: {anomalies[0].service} on {anomalies[0].date} "
            f"(${anomalies[0].amount:,.2f}, {anomalies[0].severity})."
            if anomalies
            else "No anomalies detected."
        )
    )
    state.steps_completed.append("detect_anomalies")
    return state


def step_inspect_infrastructure(db: Session, state: AgentState, include_terraform: bool) -> AgentState:
    parts = []
    if include_terraform:
        findings, files = analyze_terraform(db, persist=True)
        high = sum(1 for f in findings if f.severity == "high")
        parts.append(
            f"Terraform: analyzed {len(files)} files, {len(findings)} findings ({high} high severity)."
        )
    k8s = get_kubernetes_summary(db)
    parts.append(
        f"Kubernetes: {k8s['total_workloads']} workloads, "
        f"{k8s['unhealthy_count']} unhealthy, avg CPU {k8s['avg_cpu_percent']}%."
    )
    state.infra_inspection = " ".join(parts)
    state.steps_completed.append("inspect_infrastructure")
    return state


def step_generate_recommendations(db: Session, state: AgentState) -> AgentState:
    generate_recommendations(db)
    recs = get_all_recommendations(db)
    total_savings = sum(r.estimated_monthly_savings for r in recs)
    top = recs[:3]
    state.recommendations_summary = (
        f"Generated {len(recs)} recommendations with ${total_savings:,.2f}/mo potential savings. "
        + "Top actions: "
        + "; ".join(f"{r.title} (${r.estimated_monthly_savings:,.0f}/mo)" for r in top)
        + "."
    )
    state.steps_completed.append("generate_recommendations")
    return state


def _rule_based_summary(state: AgentState) -> str:
    return (
        "## Executive Summary\n\n"
        "**Cost Overview:** " + state.cost_analysis + "\n\n"
        "**Anomalies:** " + state.anomaly_summary + "\n\n"
        "**Infrastructure:** " + state.infra_inspection + "\n\n"
        "**Recommendations:** " + state.recommendations_summary + "\n\n"
        "**Priority Actions:**\n"
        "1. Address high-severity anomalies and security findings immediately.\n"
        "2. Right-size overprovisioned compute resources.\n"
        "3. Enable autoscaling and budget alerts to prevent future spikes.\n"
        "4. Improve tagging for accurate cost allocation.\n"
    )


def _openai_summary(state: AgentState) -> str | None:
    if not settings.openai_api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        prompt = (
            "You are a CloudOps executive advisor. Write a concise executive summary "
            "based on this operational data:\n\n"
            f"Cost Analysis: {state.cost_analysis}\n"
            f"Anomalies: {state.anomaly_summary}\n"
            f"Infrastructure: {state.infra_inspection}\n"
            f"Recommendations: {state.recommendations_summary}\n"
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a cloud cost optimization expert."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning("OpenAI summary failed, using rule-based fallback: %s", e)
        return None


def step_executive_summary(state: AgentState) -> tuple[AgentState, bool]:
    ai_summary = _openai_summary(state)
    used_openai = ai_summary is not None
    state.executive_summary = ai_summary or _rule_based_summary(state)
    state.steps_completed.append("executive_summary")
    return state, used_openai


WORKFLOW: list[tuple[str, Callable]] = [
    ("analyze_cost_data", lambda db, s, **kw: step_analyze_costs(db, s)),
    ("detect_anomalies", lambda db, s, **kw: step_detect_anomalies(db, s)),
    ("inspect_infrastructure", lambda db, s, **kw: step_inspect_infrastructure(db, s, kw.get("include_terraform", True))),
    ("generate_recommendations", lambda db, s, **kw: step_generate_recommendations(db, s)),
]


def run_agent_workflow(
    db: Session,
    include_terraform: bool = True,
    include_kubernetes: bool = True,
) -> AgentRun:
    """Execute the full LangGraph-style agent pipeline."""
    run = AgentRun(status="running", steps_completed="[]")
    db.add(run)
    db.commit()
    db.refresh(run)

    state = AgentState()

    try:
        for step_name, step_fn in WORKFLOW:
            logger.info("Agent step: %s", step_name)
            if step_name == "inspect_infrastructure":
                state = step_fn(db, state, include_terraform=include_terraform)
            else:
                state = step_fn(db, state)

        state, used_openai = step_executive_summary(state)

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.steps_completed = json.dumps(state.steps_completed)
        run.cost_analysis = state.cost_analysis
        run.anomaly_summary = state.anomaly_summary
        run.infra_inspection = state.infra_inspection
        run.recommendations_summary = state.recommendations_summary
        run.executive_summary = state.executive_summary
        run.used_openai = used_openai
        db.commit()
        db.refresh(run)
        logger.info("Agent run %d completed", run.id)
    except Exception as e:
        logger.exception("Agent run failed: %s", e)
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.executive_summary = f"Agent run failed: {e}"
        db.commit()
        db.refresh(run)

    return run
