import logging

from sqlalchemy.orm import Session

from app.models import KubernetesWorkload

logger = logging.getLogger(__name__)


def assess_health(workload: KubernetesWorkload) -> tuple[str, str | None]:
    """Determine workload health and optional fix recommendation."""
    if workload.ready_replicas < workload.replicas:
        return "unhealthy", (
            f"Only {workload.ready_replicas}/{workload.replicas} replicas ready. "
            "Check pod events and image pull status."
        )
    if workload.restart_count > 10:
        return "unhealthy", (
            f"High restart count ({workload.restart_count}). "
            "Inspect crash loop logs and liveness probe configuration."
        )
    if workload.cpu_usage_percent > 90:
        return "warning", (
            "CPU usage above 90%. Increase resource limits or add horizontal pod autoscaler."
        )
    if workload.memory_usage_percent > 90:
        return "warning", (
            "Memory usage above 90%. Increase memory limits or investigate memory leaks."
        )
    if workload.cpu_usage_percent < 5 and workload.memory_usage_percent < 10:
        return "idle", (
            "Very low utilization. Consider reducing replicas or moving to smaller node pool."
        )
    return "healthy", None


def get_kubernetes_summary(db: Session) -> dict:
    workloads = db.query(KubernetesWorkload).all()
    unhealthy = sum(1 for w in workloads if w.health in ("unhealthy", "warning"))
    idle = sum(1 for w in workloads if w.health == "idle")
    avg_cpu = sum(w.cpu_usage_percent for w in workloads) / len(workloads) if workloads else 0
    avg_mem = sum(w.memory_usage_percent for w in workloads) / len(workloads) if workloads else 0

    return {
        "total_workloads": len(workloads),
        "unhealthy_count": unhealthy,
        "idle_count": idle,
        "avg_cpu_percent": round(avg_cpu, 1),
        "avg_memory_percent": round(avg_mem, 1),
    }


def get_all_workloads(db: Session) -> list[KubernetesWorkload]:
    return db.query(KubernetesWorkload).order_by(KubernetesWorkload.namespace).all()


def refresh_workload_health(db: Session) -> None:
    workloads = db.query(KubernetesWorkload).all()
    for w in workloads:
        health, rec = assess_health(w)
        w.health = health
        w.recommendation = rec
    db.commit()
