from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import OperatingMode, settings
from app.database import Base, get_db
from app.main import app
from app.routers import api


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    def override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(api, "check_redis_health", lambda: "disconnected")
    monkeypatch.setattr(settings, "operating_mode", OperatingMode.offline)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health_exposes_mode_and_request_id(client):
    response = client.get("/health", headers={"x-request-id": "test-request"})
    assert response.status_code == 200
    assert response.json()["mode"] == "offline"
    assert response.headers["x-request-id"] == "test-request"


def test_aws_status_does_not_call_aws(client):
    response = client.get("/api/integrations/aws/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is False


def test_aws_sync_maps_provider_failure(client, monkeypatch):
    from app.integrations.aws import AWSIntegrationError
    monkeypatch.setattr(api, "sync_aws_costs", lambda db: (_ for _ in ()).throw(AWSIntegrationError("unavailable")))
    response = client.post("/api/integrations/aws/sync")
    assert response.status_code == 502
    assert response.json()["detail"] == "unavailable"


def test_aws_sync_returns_provider_summary(client, monkeypatch):
    monkeypatch.setattr(api, "cache_delete", lambda *keys: None)
    monkeypatch.setattr(api, "sync_aws_costs", lambda db: SimpleNamespace(
        account_id="111122223333", records_imported=4,
        period_start="2026-07-01", period_end="2026-07-03",
        budget_count=1, budgets_over_limit=0, estimated_month_to_date_cost=12.5,
    ))
    response = client.post("/api/integrations/aws/sync")
    assert response.status_code == 200
    assert response.json()["records_imported"] == 4
