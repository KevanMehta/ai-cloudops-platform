import json
import logging
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean, stdev

from sqlalchemy.orm import Session

from app.models import Anomaly, CloudCost

logger = logging.getLogger(__name__)

SERVICES = ["EC2", "S3", "RDS", "Lambda", "CloudFront", "EKS"]

SPIKE_THRESHOLDS = {
    "low": 1.5,
    "medium": 2.0,
    "high": 3.0,
}


def classify_severity(deviation_ratio: float) -> str:
    if deviation_ratio >= SPIKE_THRESHOLDS["high"]:
        return "high"
    if deviation_ratio >= SPIKE_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def build_explanation(
    service: str,
    cost_date: date,
    amount: float,
    expected: float,
    deviation_percent: float,
    severity: str,
) -> str:
    direction = "spike" if amount > expected else "drop"
    return (
        f"Detected a {severity} cost {direction} for {service} on {cost_date.isoformat()}. "
        f"Actual spend ${amount:,.2f} vs expected ${expected:,.2f} "
        f"({deviation_percent:+.1f}% deviation). "
        f"This exceeds the rolling 30-day baseline using mean + 2 standard deviations."
    )


def detect_anomalies(db: Session, lookback_days: int = 90) -> list[Anomaly]:
    """Detect cost anomalies per service using statistical baseline."""
    cutoff = date.today() - timedelta(days=lookback_days)
    costs = (
        db.query(CloudCost)
        .filter(CloudCost.date >= cutoff)
        .order_by(CloudCost.date)
        .all()
    )

    by_service: dict[str, list[CloudCost]] = defaultdict(list)
    for cost in costs:
        by_service[cost.service].append(cost)

    detected: list[Anomaly] = []

    for service, service_costs in by_service.items():
        daily_totals: dict[date, float] = defaultdict(float)
        for c in service_costs:
            daily_totals[c.date] += c.amount

        sorted_dates = sorted(daily_totals.keys())
        if len(sorted_dates) < 14:
            continue

        for i, cost_date in enumerate(sorted_dates):
            if i < 7:
                continue

            window_dates = sorted_dates[max(0, i - 30) : i]
            window_values = [daily_totals[d] for d in window_dates]
            if len(window_values) < 7:
                continue

            avg = mean(window_values)
            std = stdev(window_values) if len(window_values) > 1 else 0.0
            threshold = avg + max(2 * std, avg * 0.25)
            amount = daily_totals[cost_date]

            if amount <= threshold or avg == 0:
                continue

            deviation_ratio = amount / avg
            deviation_percent = ((amount - avg) / avg) * 100
            severity = classify_severity(deviation_ratio)

            existing = (
                db.query(Anomaly)
                .filter(Anomaly.service == service, Anomaly.date == cost_date)
                .first()
            )
            if existing:
                continue

            anomaly = Anomaly(
                service=service,
                date=cost_date,
                amount=round(amount, 2),
                expected_amount=round(avg, 2),
                deviation_percent=round(deviation_percent, 2),
                severity=severity,
                explanation=build_explanation(
                    service, cost_date, amount, avg, deviation_percent, severity
                ),
            )
            db.add(anomaly)
            detected.append(anomaly)

    if detected:
        db.commit()
        for a in detected:
            db.refresh(a)
        logger.info("Detected %d new anomalies", len(detected))

    return detected


def get_all_anomalies(db: Session) -> list[Anomaly]:
    return db.query(Anomaly).order_by(Anomaly.date.desc()).all()
