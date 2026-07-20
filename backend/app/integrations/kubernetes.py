import logging
from dataclasses import dataclass

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from sqlalchemy.orm import Session
from urllib3.exceptions import HTTPError

from app.config import OperatingMode, settings
from app.models import KubernetesWorkload
from app.services.kubernetes_monitor import assess_health

logger = logging.getLogger(__name__)


class KubernetesIntegrationError(RuntimeError):
    """Raised when the configured Kubernetes cluster cannot be queried."""


@dataclass(frozen=True)
class KubernetesSyncResult:
    workloads_imported: int
    context: str
    metrics_available: bool = False


def _configure_client() -> str:
    try:
        config.load_incluster_config()
        return "in-cluster"
    except config.ConfigException:
        config.load_kube_config(context=settings.kubernetes_context or None)
        return settings.kubernetes_context or "current-kubeconfig-context"


def _selector(match_labels: dict[str, str] | None) -> str:
    return ",".join(f"{key}={value}" for key, value in sorted((match_labels or {}).items()))


def _restart_count(core: client.CoreV1Api, namespace: str, labels: dict[str, str] | None) -> int:
    pods = core.list_namespaced_pod(namespace, label_selector=_selector(labels)).items
    return sum(
        status.restart_count
        for pod in pods
        for status in (pod.status.container_statuses or [])
    )


def _from_controller(item, workload_type: str, core: client.CoreV1Api) -> KubernetesWorkload:
    desired = item.spec.replicas or 0
    ready = item.status.ready_replicas or 0
    workload = KubernetesWorkload(
        namespace=item.metadata.namespace,
        name=item.metadata.name,
        workload_type=workload_type,
        replicas=desired,
        ready_replicas=ready,
        cpu_usage_percent=-1.0,
        memory_usage_percent=-1.0,
        restart_count=_restart_count(core, item.metadata.namespace, item.spec.selector.match_labels),
        status="Running" if ready == desired else "Degraded",
        health="healthy",
    )
    workload.health, workload.recommendation = assess_health(workload)
    return workload


def sync_kubernetes_workloads(db: Session) -> KubernetesSyncResult:
    if settings.operating_mode is not OperatingMode.connected:
        raise KubernetesIntegrationError("Kubernetes synchronization requires OPERATING_MODE=connected")
    try:
        context = _configure_client()
        apps = client.AppsV1Api()
        core = client.CoreV1Api()
        workloads = [
            *(_from_controller(item, "Deployment", core) for item in apps.list_deployment_for_all_namespaces().items),
            *(_from_controller(item, "StatefulSet", core) for item in apps.list_stateful_set_for_all_namespaces().items),
        ]
    except (ApiException, config.ConfigException, HTTPError, OSError) as exc:
        logger.warning("Kubernetes synchronization failed", extra={"error_type": type(exc).__name__})
        raise KubernetesIntegrationError("Kubernetes synchronization failed; check cluster access and RBAC") from exc

    try:
        db.query(KubernetesWorkload).delete()
        db.add_all(workloads)
        db.commit()
    except Exception:
        db.rollback()
        raise
    logger.info("Kubernetes synchronization completed", extra={"workloads_imported": len(workloads)})
    return KubernetesSyncResult(len(workloads), context)
