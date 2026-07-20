from datetime import date
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import OperatingMode, settings
from app.database import Base
from app.integrations import aws
from app.models import CloudCost


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class FakePaginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **kwargs):
        return iter(self.pages)


def test_fetch_cost_records_maps_cost_explorer_groups():
    page = {
        "ResultsByTime": [{
            "TimePeriod": {"Start": "2026-07-01", "End": "2026-07-02"},
            "Groups": [{
                "Keys": ["Amazon Elastic Compute Cloud - Compute", "us-east-1"],
                "Metrics": {"UnblendedCost": {"Amount": "12.3456789", "Unit": "USD"}},
            }],
        }]
    }
    ce = SimpleNamespace(get_paginator=lambda name: FakePaginator([page]))
    session = SimpleNamespace(client=lambda service, **kwargs: ce)

    records = aws.fetch_cost_records(session, date(2026, 7, 1), date(2026, 7, 2))

    assert records == [{
        "date": date(2026, 7, 1),
        "service": "Amazon Elastic Compute Cloud - Compute",
        "region": "us-east-1",
        "amount": 12.345679,
    }]


def test_sync_aws_costs_persists_only_after_provider_calls_succeed(db_session, monkeypatch):
    monkeypatch.setattr(settings, "operating_mode", OperatingMode.connected)
    fake_session = SimpleNamespace(
        client=lambda service: SimpleNamespace(get_caller_identity=lambda: {"Account": "111122223333"})
    )
    monkeypatch.setattr(aws, "_session", lambda: fake_session)
    monkeypatch.setattr(aws, "fetch_cost_records", lambda *args: [{
        "date": date.today(), "service": "Amazon S3", "region": "us-east-1", "amount": 2.5,
    }])
    monkeypatch.setattr(aws, "fetch_budget_summary", lambda *args: (2, 1))
    monkeypatch.setattr(aws, "fetch_estimated_month_to_date_cost", lambda *args: 42.0)

    result = aws.sync_aws_costs(db_session)

    assert result.account_id == "111122223333"
    assert result.records_imported == 1
    assert result.budgets_over_limit == 1
    assert db_session.query(CloudCost).one().amount == 2.5


def test_sync_aws_costs_wraps_credential_failure(db_session, monkeypatch):
    monkeypatch.setattr(settings, "operating_mode", OperatingMode.connected)
    error = ClientError({"Error": {"Code": "AccessDenied", "Message": "denied"}}, "AssumeRole")
    monkeypatch.setattr(aws, "_session", lambda: (_ for _ in ()).throw(error))

    with pytest.raises(aws.AWSIntegrationError, match="credentials"):
        aws.sync_aws_costs(db_session)


def test_sync_aws_costs_rejects_demo_mode(db_session, monkeypatch):
    monkeypatch.setattr(settings, "operating_mode", OperatingMode.demo)
    with pytest.raises(aws.AWSIntegrationError, match="connected"):
        aws.sync_aws_costs(db_session)
