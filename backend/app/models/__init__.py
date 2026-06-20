from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CloudCost(Base):
    __tablename__ = "cloud_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str] = mapped_column(String(32), default="us-east-1")
    account_id: Mapped[str] = mapped_column(String(32), default="123456789012")


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    service: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    expected_amount: Mapped[float] = mapped_column(Float, nullable=False)
    deviation_percent: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(default=False)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    estimated_monthly_savings: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    action_steps: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="engine")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), default="running")
    steps_completed: Mapped[str] = mapped_column(Text, default="[]")
    cost_analysis: Mapped[Optional[str]] = mapped_column(Text)
    anomaly_summary: Mapped[Optional[str]] = mapped_column(Text)
    infra_inspection: Mapped[Optional[str]] = mapped_column(Text)
    recommendations_summary: Mapped[Optional[str]] = mapped_column(Text)
    executive_summary: Mapped[Optional[str]] = mapped_column(Text)
    used_openai: Mapped[bool] = mapped_column(default=False)


class TerraformFinding(Base):
    __tablename__ = "terraform_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(String(256), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(128), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class KubernetesWorkload(Base):
    __tablename__ = "kubernetes_workloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    namespace: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    workload_type: Mapped[str] = mapped_column(String(32), default="Deployment")
    replicas: Mapped[int] = mapped_column(Integer, default=1)
    ready_replicas: Mapped[int] = mapped_column(Integer, default=1)
    cpu_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_usage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    restart_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    health: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
