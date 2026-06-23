import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Anomaly, CloudCost, Recommendation
from app.schemas import (
    CostTrendPoint,
    DashboardResponse,
    ServiceBreakdown,
)
from app.services.recommendations import get_all_recommendations

logger = logging.getLogger(__name__)


def get_service_breakdown(db: Session, days: int = 30) -> list[ServiceBreakdown]:
    cutoff = date.today() - timedelta(days=days)
    rows = (
        db.query(CloudCost.service, func.sum(CloudCost.amount).label("total"))
        .filter(CloudCost.date >= cutoff)
        .group_by(CloudCost.service)
        .order_by(func.sum(CloudCost.amount).desc())
        .all()
    )
    grand_total = sum(r.total for r in rows) or 1.0
    return [
        ServiceBreakdown(
            service=r.service,
            total=round(float(r.total), 2),
            percentage=round(float(r.total) / grand_total * 100, 1),
        )
        for r in rows
    ]


def get_cost_trend(db: Session, days: int = 30) -> list[CostTrendPoint]:
    cutoff = date.today() - timedelta(days=days)
    rows = (
        db.query(CloudCost.date, func.sum(CloudCost.amount).label("total"))
        .filter(CloudCost.date >= cutoff)
        .group_by(CloudCost.date)
        .order_by(CloudCost.date)
        .all()
    )
    return [
        CostTrendPoint(date=r.date, amount=round(float(r.total), 2))
        for r in rows
    ]


def get_dashboard(db: Session) -> DashboardResponse:
    month_start = date.today().replace(day=1)
    month_costs = (
        db.query(func.sum(CloudCost.amount))
        .filter(CloudCost.date >= month_start)
        .scalar()
        or 0.0
    )

    trend = get_cost_trend(db, days=30)
    if len(trend) >= 7:
        recent_avg = sum(p.amount for p in trend[-7:]) / 7
        projected = round(recent_avg * 30, 2)
    else:
        projected = round(float(month_costs) * 1.1, 2)

    anomaly_count = db.query(Anomaly).count()
    breakdown = get_service_breakdown(db, days=30)
    top_services = breakdown[:5]
    recommendations = get_all_recommendations(db)[:5]

    return DashboardResponse(
        total_monthly_spend=round(float(month_costs), 2),
        projected_spend=projected,
        anomaly_count=anomaly_count,
        top_expensive_services=top_services,
        cost_trend=trend,
        service_breakdown=breakdown,
        optimization_recommendations=recommendations,
    )


def get_costs(db: Session, days: int = 90) -> tuple[list[CloudCost], float, list[ServiceBreakdown], list[CostTrendPoint]]:
    cutoff = date.today() - timedelta(days=days)
    costs = (
        db.query(CloudCost)
        .filter(CloudCost.date >= cutoff)
        .order_by(CloudCost.date.desc())
        .all()
    )
    total = sum(c.amount for c in costs)
    by_service = get_service_breakdown(db, days=days)
    trend = get_cost_trend(db, days=days)
    return costs, round(total, 2), by_service, trend
