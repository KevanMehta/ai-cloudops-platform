import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy.orm import Session

from app.config import OperatingMode, settings
from app.models import CloudCost

logger = logging.getLogger(__name__)


class AWSIntegrationError(RuntimeError):
    """Raised when an AWS request cannot be completed safely."""


@dataclass(frozen=True)
class AWSSyncResult:
    account_id: str
    records_imported: int
    period_start: date
    period_end: date
    budget_count: int
    budgets_over_limit: int
    estimated_month_to_date_cost: float | None
    warnings: list[str] = field(default_factory=list)


def _session() -> boto3.Session:
    base = boto3.Session(region_name=settings.aws_region)
    if not settings.aws_role_arn:
        return base

    request = {
        "RoleArn": settings.aws_role_arn,
        "RoleSessionName": settings.aws_session_name,
    }
    if settings.aws_external_id:
        request["ExternalId"] = settings.aws_external_id
    response = base.client("sts").assume_role(**request)
    credentials = response["Credentials"]
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
        region_name=settings.aws_region,
    )


def _amount(value: str | None) -> float:
    try:
        return float(Decimal(value or "0"))
    except (InvalidOperation, ValueError) as exc:
        raise AWSIntegrationError(f"AWS returned an invalid monetary amount: {value!r}") from exc


def fetch_cost_records(session: boto3.Session, start: date, end: date) -> list[dict]:
    """Fetch daily unblended costs. Cost Explorer end dates are exclusive."""
    client = session.client("ce", region_name="us-east-1")
    paginator = client.get_paginator("get_cost_and_usage")
    records: list[dict] = []
    for page in paginator.paginate(
        TimePeriod={"Start": start.isoformat(), "End": end.isoformat()},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "DIMENSION", "Key": "REGION"},
        ],
    ):
        for period in page.get("ResultsByTime", []):
            cost_date = date.fromisoformat(period["TimePeriod"]["Start"])
            for group in period.get("Groups", []):
                service, region = (group.get("Keys", []) + ["", ""])[:2]
                amount = _amount(group.get("Metrics", {}).get("UnblendedCost", {}).get("Amount"))
                if amount == 0:
                    continue
                records.append(
                    {
                        "date": cost_date,
                        "service": service or "Unknown",
                        "region": region or "global",
                        "amount": round(amount, 6),
                    }
                )
    return records


def fetch_budget_summary(session: boto3.Session, account_id: str) -> tuple[int, int]:
    client = session.client("budgets", region_name="us-east-1")
    count = 0
    over_limit = 0
    paginator = client.get_paginator("describe_budgets")
    for page in paginator.paginate(AccountId=account_id):
        for budget in page.get("Budgets", []):
            count += 1
            actual = _amount(budget.get("CalculatedSpend", {}).get("ActualSpend", {}).get("Amount"))
            limit = _amount(budget.get("BudgetLimit", {}).get("Amount"))
            if limit > 0 and actual > limit:
                over_limit += 1
    return count, over_limit


def fetch_estimated_month_to_date_cost(session: boto3.Session) -> float | None:
    """Read the account-level CloudWatch Billing metric when billing alerts expose it."""
    client = session.client("cloudwatch", region_name="us-east-1")
    now = datetime.now(timezone.utc)
    response = client.get_metric_data(
        MetricDataQueries=[
            {
                "Id": "estimatedcharges",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/Billing",
                        "MetricName": "EstimatedCharges",
                        "Dimensions": [{"Name": "Currency", "Value": "USD"}],
                    },
                    "Period": 21600,
                    "Stat": "Maximum",
                },
                "ReturnData": True,
            }
        ],
        StartTime=now - timedelta(days=2),
        EndTime=now,
        ScanBy="TimestampDescending",
        MaxDatapoints=1,
    )
    values = response.get("MetricDataResults", [{}])[0].get("Values", [])
    return round(float(values[0]), 2) if values else None


def sync_aws_costs(db: Session) -> AWSSyncResult:
    if settings.operating_mode is not OperatingMode.connected:
        raise AWSIntegrationError("AWS synchronization requires OPERATING_MODE=connected")

    start = date.today() - timedelta(days=settings.aws_cost_lookback_days)
    end = date.today() + timedelta(days=1)
    try:
        session = _session()
        identity = session.client("sts").get_caller_identity()
        account_id = identity["Account"]
        records = fetch_cost_records(session, start, end)
        warnings: list[str] = []
        try:
            budget_count, budgets_over_limit = fetch_budget_summary(session, account_id)
        except (BotoCoreError, ClientError, AWSIntegrationError):
            budget_count, budgets_over_limit = 0, 0
            warnings.append("Budgets data unavailable; verify budgets:ViewBudget permission")
        try:
            estimated = fetch_estimated_month_to_date_cost(session)
        except (BotoCoreError, ClientError):
            estimated = None
            warnings.append("CloudWatch billing metric unavailable; verify cloudwatch:GetMetricData permission and billing alerts")
    except (BotoCoreError, ClientError, KeyError, AWSIntegrationError) as exc:
        logger.warning("AWS synchronization failed", extra={"error_type": type(exc).__name__})
        raise AWSIntegrationError("AWS synchronization failed; check credentials, role trust, region, and permissions") from exc

    try:
        db.query(CloudCost).filter(
            CloudCost.account_id == account_id,
            CloudCost.date >= start,
            CloudCost.date < end,
        ).delete(synchronize_session=False)
        db.add_all(CloudCost(account_id=account_id, **record) for record in records)
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info(
        "AWS cost synchronization completed",
        extra={"account_id": account_id, "records_imported": len(records)},
    )
    return AWSSyncResult(
        account_id=account_id,
        records_imported=len(records),
        period_start=start,
        period_end=end,
        budget_count=budget_count,
        budgets_over_limit=budgets_over_limit,
        estimated_month_to_date_cost=estimated,
        warnings=warnings,
    )
