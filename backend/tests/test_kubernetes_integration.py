from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import OperatingMode, settings
from app.database import Base
from app.integrations import kubernetes as integration
from app.models import KubernetesWorkload
from app.services.kubernetes_monitor import assess_health


def _controller(name="api", replicas=2, ready=2):
    return SimpleNamespace(
        metadata=SimpleNamespace(name=name, namespace="default"),
        spec=SimpleNamespace(replicas=replicas, selector=SimpleNamespace(match_labels={"app": name})),
        status=SimpleNamespace(ready_replicas=ready),
    )


def test_live_workload_without_metrics_is_not_classified_idle():
    workload = KubernetesWorkload(
        namespace="default", name="api", workload_type="Deployment", replicas=2,
        ready_replicas=2, cpu_usage_percent=-1, memory_usage_percent=-1,
        restart_count=0, status="Running", health="healthy",
    )
    health, recommendation = assess_health(workload)
    assert health == "healthy"
    assert recommendation is None


def test_sync_kubernetes_replaces_snapshot(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    monkeypatch.setattr(settings, "operating_mode", OperatingMode.connected)
    monkeypatch.setattr(integration, "_configure_client", lambda: "test-context")
    apps = SimpleNamespace(
        list_deployment_for_all_namespaces=lambda: SimpleNamespace(items=[_controller()]),
        list_stateful_set_for_all_namespaces=lambda: SimpleNamespace(items=[]),
    )
    core = SimpleNamespace(list_namespaced_pod=lambda *args, **kwargs: SimpleNamespace(items=[]))
    monkeypatch.setattr(integration.client, "AppsV1Api", lambda: apps)
    monkeypatch.setattr(integration.client, "CoreV1Api", lambda: core)

    result = integration.sync_kubernetes_workloads(db)

    assert result.workloads_imported == 1
    stored = db.query(KubernetesWorkload).one()
    assert stored.name == "api"
    assert stored.cpu_usage_percent == -1
    db.close()
