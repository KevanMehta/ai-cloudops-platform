import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CloudCost, Anomaly, TerraformFinding, KubernetesWorkload, Recommendation
from app.services.recommendations import generate_recommendations, get_all_recommendations


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def seed_costs(session, days=30):
    today = date.today()
    services = {"EC2": 850, "S3": 150, "RDS": 400, "Lambda": 60, "CloudFront": 100, "EKS": 350}
    for i in range(days):
        d = today - timedelta(days=days - i)
        for svc, base in services.items():
            session.add(CloudCost(date=d, service=svc, amount=base, region="us-east-1"))
    session.commit()


def test_recommendation_has_required_fields(db_session):
    seed_costs(db_session)
    generate_recommendations(db_session)
    recs = get_all_recommendations(db_session)
    assert len(recs) >= 1
    for r in recs:
        assert r.title
        assert r.severity in ("low", "medium", "high")
        assert r.estimated_monthly_savings >= 0
        assert r.explanation
        assert r.action_steps


def test_recommendation_deduplication(db_session):
    seed_costs(db_session)
    first = generate_recommendations(db_session)
    second = generate_recommendations(db_session)
    assert len(first) >= 1
    assert len(second) == 0


def test_anomaly_recommendations(db_session):
    seed_costs(db_session)
    db_session.add(
        Anomaly(
            service="EC2",
            date=date.today() - timedelta(days=1),
            amount=3500.0,
            expected_amount=850.0,
            deviation_percent=311.0,
            severity="high",
            explanation="Major EC2 spike detected",
        )
    )
    db_session.commit()

    recs = generate_recommendations(db_session)
    assert any("Investigate" in r.title for r in recs)


def test_public_storage_recommendation(db_session):
    seed_costs(db_session)
    db_session.add(
        TerraformFinding(
            file_name="s3.tf",
            resource_type="aws_s3_bucket",
            resource_name="public_assets",
            issue_type="public_storage",
            severity="high",
            description="Public bucket",
            recommendation="Block public access",
        )
    )
    db_session.commit()

    recs = generate_recommendations(db_session)
    assert any("public" in r.title.lower() or "S3" in r.title for r in recs)
