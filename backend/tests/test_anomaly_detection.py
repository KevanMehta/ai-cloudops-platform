import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CloudCost, Anomaly
from app.services.anomaly_detection import (
    classify_severity,
    detect_anomalies,
    build_explanation,
)
from app.services.recommendations import generate_recommendations
from app.models import Recommendation, TerraformFinding, KubernetesWorkload


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def seed_normal_costs(session, service="EC2", base=100.0, days=60):
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=days - i)
        session.add(CloudCost(date=d, service=service, amount=base, region="us-east-1"))
    session.commit()


def test_classify_severity():
    assert classify_severity(3.5) == "high"
    assert classify_severity(2.5) == "medium"
    assert classify_severity(1.6) == "low"


def test_build_explanation():
    text = build_explanation("EC2", date(2025, 1, 1), 500.0, 100.0, 400.0, "high")
    assert "EC2" in text
    assert "high" in text
    assert "$500.00" in text


def test_detect_anomalies_finds_spike(db_session):
    seed_normal_costs(db_session, service="RDS", base=200.0, days=45)
    spike_date = date.today() - timedelta(days=2)
    db_session.add(
        CloudCost(date=spike_date, service="RDS", amount=900.0, region="us-east-1")
    )
    db_session.commit()

    detected = detect_anomalies(db_session, lookback_days=90)
    assert len(detected) >= 1
    assert any(a.service == "RDS" for a in detected)


def test_detect_anomalies_severity_levels(db_session):
    seed_normal_costs(db_session, service="Lambda", base=50.0, days=45)
    spike_date = date.today() - timedelta(days=1)
    db_session.add(
        CloudCost(date=spike_date, service="Lambda", amount=250.0, region="us-east-1")
    )
    db_session.commit()

    detected = detect_anomalies(db_session)
    assert all(a.severity in ("low", "medium", "high") for a in detected)


def test_no_duplicate_anomalies(db_session):
    seed_normal_costs(db_session, service="S3", base=80.0, days=45)
    spike_date = date.today() - timedelta(days=3)
    db_session.add(
        CloudCost(date=spike_date, service="S3", amount=400.0, region="us-east-1")
    )
    db_session.commit()

    first = detect_anomalies(db_session)
    second = detect_anomalies(db_session)
    assert len(first) >= 1
    assert len(second) == 0


def test_generate_recommendations_budget_alert(db_session):
    seed_normal_costs(db_session, service="EC2", base=900.0, days=30)
    seed_normal_costs(db_session, service="S3", base=100.0, days=30)

    recs = generate_recommendations(db_session)
    assert len(recs) >= 1
    titles = [r.title for r in db_session.query(Recommendation).all()]
    assert any("budget" in t.lower() for t in titles)


def test_generate_recommendations_from_terraform(db_session):
    db_session.add(
        TerraformFinding(
            file_name="ec2.tf",
            resource_type="aws_instance",
            resource_name="web",
            issue_type="missing_autoscaling",
            severity="medium",
            description="No ASG",
            recommendation="Add ASG",
        )
    )
    db_session.commit()

    recs = generate_recommendations(db_session)
    titles = [r.title for r in recs]
    assert any("autoscaling" in t.lower() for t in titles)


def test_generate_recommendations_from_k8s_idle(db_session):
    db_session.add(
        KubernetesWorkload(
            namespace="staging",
            name="idle-app",
            workload_type="Deployment",
            replicas=1,
            ready_replicas=1,
            cpu_usage_percent=3.0,
            memory_usage_percent=5.0,
            restart_count=0,
            status="Running",
            health="idle",
        )
    )
    db_session.commit()

    recs = generate_recommendations(db_session)
    titles = [r.title for r in recs]
    assert any("idle" in t.lower() for t in titles)
