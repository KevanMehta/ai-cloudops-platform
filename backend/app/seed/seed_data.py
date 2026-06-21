import logging
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Anomaly,
    CloudCost,
    KubernetesWorkload,
)
from app.services.anomaly_detection import SERVICES, build_explanation, classify_severity
from app.services.kubernetes_monitor import assess_health
from app.services.anomaly_detection import detect_anomalies
from app.services.recommendations import generate_recommendations
from app.services.terraform_analyzer import analyze_terraform
from app.database import Base, engine

logger = logging.getLogger(__name__)

# Base daily costs per service (realistic AWS-like values)
BASE_COSTS = {
    "EC2": 920.0,
    "S3": 180.0,
    "RDS": 450.0,
    "Lambda": 65.0,
    "CloudFront": 120.0,
    "EKS": 380.0,
}

# Intentional anomaly spikes (day offset from today, service, multiplier)
INTENTIONAL_ANOMALIES = [
    (-45, "EC2", 3.8),
    (-32, "RDS", 2.9),
    (-21, "Lambda", 4.2),
    (-14, "S3", 3.1),
    (-7, "EKS", 2.6),
    (-3, "CloudFront", 3.5),
    (-1, "EC2", 2.2),
]

K8S_WORKLOADS = [
    ("production", "api-gateway", "Deployment", 3, 3, 45.2, 62.1, 0, "Running"),
    ("production", "payment-service", "Deployment", 2, 2, 78.5, 81.3, 1, "Running"),
    ("production", "user-service", "Deployment", 3, 2, 55.0, 48.0, 15, "Running"),
    ("staging", "frontend", "Deployment", 2, 2, 12.3, 18.7, 0, "Running"),
    ("staging", "batch-processor", "Deployment", 1, 1, 3.2, 8.5, 0, "Running"),
    ("production", "cache-redis", "StatefulSet", 3, 3, 92.1, 88.4, 2, "Running"),
    ("monitoring", "prometheus", "StatefulSet", 1, 1, 67.0, 72.0, 0, "Running"),
    ("production", "legacy-monolith", "Deployment", 2, 1, 95.0, 93.0, 22, "Running"),
]


def seed_cloud_costs(db: Session) -> None:
    if db.query(CloudCost).count() > 0:
        return

    today = date.today()
    random.seed(42)
    records: list[CloudCost] = []

    for day_offset in range(90, 0, -1):
        cost_date = today - timedelta(days=day_offset)
        for service, base in BASE_COSTS.items():
            noise = random.uniform(0.85, 1.15)
            amount = base * noise

            for anomaly_offset, anomaly_service, multiplier in INTENTIONAL_ANOMALIES:
                anomaly_date = today + timedelta(days=anomaly_offset)
                if cost_date == anomaly_date and service == anomaly_service:
                    amount = base * multiplier

            records.append(
                CloudCost(
                    date=cost_date,
                    service=service,
                    amount=round(amount, 2),
                    region="us-east-1",
                    account_id="123456789012",
                )
            )

    db.add_all(records)
    db.commit()
    logger.info("Seeded %d cloud cost records", len(records))


def seed_intentional_anomalies(db: Session) -> None:
    if db.query(Anomaly).count() > 0:
        return

    today = date.today()
    anomalies: list[Anomaly] = []

    for day_offset, service, multiplier in INTENTIONAL_ANOMALIES:
        anomaly_date = today + timedelta(days=day_offset)
        base = BASE_COSTS[service]
        amount = round(base * multiplier, 2)
        expected = round(base * 1.0, 2)
        deviation = ((amount - expected) / expected) * 100
        severity = classify_severity(multiplier)

        anomalies.append(
            Anomaly(
                service=service,
                date=anomaly_date,
                amount=amount,
                expected_amount=expected,
                deviation_percent=round(deviation, 2),
                severity=severity,
                explanation=build_explanation(
                    service, anomaly_date, amount, expected, deviation, severity
                ),
            )
        )

    db.add_all(anomalies)
    db.commit()
    logger.info("Seeded %d intentional anomalies", len(anomalies))


def seed_kubernetes(db: Session) -> None:
    if db.query(KubernetesWorkload).count() > 0:
        return

    workloads: list[KubernetesWorkload] = []
    for ns, name, wtype, replicas, ready, cpu, mem, restarts, status in K8S_WORKLOADS:
        w = KubernetesWorkload(
            namespace=ns,
            name=name,
            workload_type=wtype,
            replicas=replicas,
            ready_replicas=ready,
            cpu_usage_percent=cpu,
            memory_usage_percent=mem,
            restart_count=restarts,
            status=status,
            health="healthy",
        )
        health, rec = assess_health(w)
        w.health = health
        w.recommendation = rec
        workloads.append(w)

    db.add_all(workloads)
    db.commit()
    logger.info("Seeded %d kubernetes workloads", len(workloads))


def init_database(db: Session) -> None:
    Base.metadata.create_all(bind=engine)
    seed_cloud_costs(db)
    seed_intentional_anomalies(db)
    seed_kubernetes(db)
    from app.models import Recommendation, TerraformFinding

    if db.query(TerraformFinding).count() == 0:
        analyze_terraform(db, persist=True)
    detect_anomalies(db)
    if db.query(Recommendation).count() == 0:
        generate_recommendations(db)
    logger.info("Database initialization complete")
