import json
import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import Anomaly, CloudCost, KubernetesWorkload, Recommendation, TerraformFinding

logger = logging.getLogger(__name__)


def _format_steps(steps: list[str]) -> str:
    return json.dumps(steps)


def generate_recommendations(db: Session) -> list[Recommendation]:
    """Generate actionable recommendations from cost, infra, and k8s data."""
    existing_titles = {r.title for r in db.query(Recommendation.title).all()}
    new_recs: list[Recommendation] = []

    # Cost-based: overprovisioned EC2
    ec2_costs = (
        db.query(CloudCost)
        .filter(CloudCost.service == "EC2")
        .order_by(CloudCost.date.desc())
        .limit(30)
        .all()
    )
    if ec2_costs:
        avg_ec2 = sum(c.amount for c in ec2_costs) / len(ec2_costs)
        title = "Reduce overprovisioned EC2 instances"
        if title not in existing_titles and avg_ec2 > 800:
            new_recs.append(
                Recommendation(
                    title=title,
                    category="cost_optimization",
                    severity="high",
                    estimated_monthly_savings=round(avg_ec2 * 0.25 * 30, 2),
                    explanation=(
                        f"EC2 daily spend averages ${avg_ec2:,.2f}. "
                        "Right-sizing instances and removing idle capacity can reduce costs by ~25%."
                    ),
                    action_steps=_format_steps([
                        "Audit EC2 instance utilization via CloudWatch metrics",
                        "Downsize m5.2xlarge instances with <20% CPU utilization",
                        "Convert steady-state workloads to Reserved Instances or Savings Plans",
                        "Enable AWS Compute Optimizer recommendations",
                    ]),
                    source="engine",
                )
            )

    # Autoscaling recommendation from terraform findings
    missing_asg = (
        db.query(TerraformFinding)
        .filter(TerraformFinding.issue_type == "missing_autoscaling")
        .count()
    )
    if missing_asg > 0:
        title = "Add autoscaling to web tier"
        if title not in existing_titles:
            new_recs.append(
                Recommendation(
                    title=title,
                    category="infrastructure",
                    severity="medium",
                    estimated_monthly_savings=1200.0,
                    explanation=(
                        f"Found {missing_asg} Terraform resource(s) without autoscaling. "
                        "Fixed capacity leads to over-provisioning during low traffic."
                    ),
                    action_steps=_format_steps([
                        "Create an Auto Scaling Group for the web tier",
                        "Configure target tracking on CPU at 60%",
                        "Set min=2, max=10 instances based on traffic patterns",
                        "Add scheduled scaling for known peak hours",
                    ]),
                    source="terraform",
                )
            )

    # Public storage
    public_s3 = (
        db.query(TerraformFinding)
        .filter(TerraformFinding.issue_type == "public_storage")
        .count()
    )
    if public_s3 > 0:
        title = "Restrict public S3 bucket access"
        if title not in existing_titles:
            new_recs.append(
                Recommendation(
                    title=title,
                    category="security",
                    severity="high",
                    estimated_monthly_savings=0.0,
                    explanation=(
                        "Public S3 buckets expose data and can incur unexpected egress costs. "
                        "Restrict access immediately."
                    ),
                    action_steps=_format_steps([
                        "Enable S3 Block Public Access at account level",
                        "Remove public ACLs and bucket policies",
                        "Use CloudFront with OAI for public content delivery",
                        "Enable S3 access logging for audit trail",
                    ]),
                    source="terraform",
                )
            )

    # Tagging
    missing_tags = (
        db.query(TerraformFinding)
        .filter(TerraformFinding.issue_type == "missing_tags")
        .count()
    )
    if missing_tags > 0:
        title = "Improve resource tagging for cost allocation"
        if title not in existing_titles:
            new_recs.append(
                Recommendation(
                    title=title,
                    category="governance",
                    severity="low",
                    estimated_monthly_savings=500.0,
                    explanation=(
                        f"{missing_tags} resources lack required cost allocation tags. "
                        "Proper tagging enables chargeback and waste identification."
                    ),
                    action_steps=_format_steps([
                        "Define mandatory tags: Environment, Team, CostCenter",
                        "Apply AWS Config rule for required tags",
                        "Retroactively tag existing resources via Resource Groups Tagging API",
                        "Enable cost allocation tags in AWS Billing console",
                    ]),
                    source="terraform",
                )
            )

    # Anomaly-based recommendations
    high_anomalies = (
        db.query(Anomaly).filter(Anomaly.severity == "high").limit(5).all()
    )
    for anomaly in high_anomalies:
        title = f"Investigate {anomaly.service} cost spike on {anomaly.date}"
        if title not in existing_titles:
            new_recs.append(
                Recommendation(
                    title=title,
                    category="anomaly",
                    severity="high",
                    estimated_monthly_savings=round(anomaly.amount * 20, 2),
                    explanation=anomaly.explanation,
                    action_steps=_format_steps([
                        f"Review {anomaly.service} usage on {anomaly.date}",
                        "Check for deployment changes or traffic spikes",
                        "Validate billing line items in Cost Explorer",
                        "Set up AWS Budget alert for this service",
                    ]),
                    source="anomaly",
                )
            )

    # Kubernetes idle workloads
    idle_workloads = (
        db.query(KubernetesWorkload)
        .filter(
            KubernetesWorkload.cpu_usage_percent < 10,
            KubernetesWorkload.memory_usage_percent < 15,
        )
        .all()
    )
    if idle_workloads:
        title = "Move idle Kubernetes workloads to smaller nodes"
        if title not in existing_titles:
            savings = len(idle_workloads) * 150.0
            new_recs.append(
                Recommendation(
                    title=title,
                    category="kubernetes",
                    severity="medium",
                    estimated_monthly_savings=savings,
                    explanation=(
                        f"{len(idle_workloads)} workloads show very low resource utilization. "
                        "Consolidating onto smaller node groups reduces compute waste."
                    ),
                    action_steps=_format_steps([
                        "Identify workloads with CPU < 10% and memory < 15%",
                        "Adjust resource requests and limits to match actual usage",
                        "Enable cluster autoscaler with appropriate node group sizing",
                        "Consider spot instances for fault-tolerant workloads",
                    ]),
                    source="kubernetes",
                )
            )

    # Budget alerts
    title = "Add budget alerts for top spending services"
    if title not in existing_titles:
        service_totals: dict[str, float] = defaultdict(float)
        cutoff = date.today() - timedelta(days=30)
        for cost in db.query(CloudCost).filter(CloudCost.date >= cutoff).all():
            service_totals[cost.service] += cost.amount
        top_service = max(service_totals, key=service_totals.get) if service_totals else "EC2"
        new_recs.append(
            Recommendation(
                title=title,
                category="governance",
                severity="medium",
                estimated_monthly_savings=800.0,
                explanation=(
                    f"Top spender is {top_service} at ${service_totals.get(top_service, 0):,.2f}/month. "
                    "Budget alerts prevent surprise overruns."
                ),
                action_steps=_format_steps([
                    "Create AWS Budget for each major service",
                    "Set alert thresholds at 80%, 100%, and 120% of forecast",
                    "Route alerts to Slack via SNS",
                    "Review budget vs actual weekly in team standup",
                ]),
                source="engine",
            )
        )

    if new_recs:
        db.add_all(new_recs)
        db.commit()
        for r in new_recs:
            db.refresh(r)
        logger.info("Generated %d new recommendations", len(new_recs))

    return new_recs


def get_all_recommendations(db: Session) -> list[Recommendation]:
    return (
        db.query(Recommendation)
        .order_by(Recommendation.estimated_monthly_savings.desc())
        .all()
    )
