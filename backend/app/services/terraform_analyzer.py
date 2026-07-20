import logging
from pathlib import Path

import hcl2
from lark.exceptions import UnexpectedInput
from sqlalchemy.orm import Session

from app.config import settings
from app.models import TerraformFinding

logger = logging.getLogger(__name__)

INSTANCE_TYPES = {
    "m5.4xlarge": "high",
    "m5.2xlarge": "medium",
    "r5.4xlarge": "high",
    "p3.2xlarge": "high",
}
REQUIRED_TAGS = {"Environment", "Team", "CostCenter"}


class TerraformParseError(ValueError):
    pass


def _finding(file_name: str, resource_type: str, resource_name: str, **values) -> dict:
    return {
        "file_name": file_name,
        "resource_type": resource_type,
        "resource_name": resource_name,
        **values,
    }


def _tags(attributes: dict) -> set[str]:
    tags = attributes.get("tags", {})
    return set(tags) if isinstance(tags, dict) else set()


def analyze_resource(file_name: str, resource_type: str, resource_name: str, attrs: dict) -> list[dict]:
    findings: list[dict] = []
    tags = _tags(attrs)

    if resource_type == "aws_instance":
        instance_type = str(attrs.get("instance_type", ""))
        if instance_type in INSTANCE_TYPES or "xlarge" in instance_type:
            findings.append(_finding(
                file_name, resource_type, resource_name,
                issue_type="overprovisioned_instance",
                severity=INSTANCE_TYPES.get(instance_type, "medium"),
                description=f"Instance type {instance_type} warrants utilization review before deployment.",
                recommendation="Compare CloudWatch utilization and Compute Optimizer data before selecting a smaller type.",
            ))

    if resource_type == "aws_s3_bucket":
        acl = str(attrs.get("acl", ""))
        if acl in {"public-read", "public-read-write"}:
            findings.append(_finding(
                file_name, resource_type, resource_name,
                issue_type="public_storage",
                severity="high",
                description=f"S3 bucket '{resource_name}' declares the public ACL '{acl}'.",
                recommendation="Remove the public ACL and enable S3 Block Public Access unless public access is explicitly required.",
            ))

    if resource_type == "aws_db_instance":
        instance_class = str(attrs.get("instance_class", ""))
        if "xlarge" in instance_class:
            findings.append(_finding(
                file_name, resource_type, resource_name,
                issue_type="overprovisioned_instance",
                severity="medium",
                description=f"RDS instance class {instance_class} warrants a utilization review.",
                recommendation="Review Performance Insights and CloudWatch metrics before changing the instance class.",
            ))

    if resource_type == "aws_autoscaling_group":
        minimum = attrs.get("min_size")
        maximum = attrs.get("max_size")
        if minimum is not None and maximum is not None and minimum == maximum:
            findings.append(_finding(
                file_name, resource_type, resource_name,
                issue_type="fixed_capacity",
                severity="medium",
                description=f"ASG '{resource_name}' has fixed capacity (min=max={minimum}).",
                recommendation="Confirm fixed capacity is intentional or add a target-tracking scaling policy.",
            ))

    taggable = resource_type.startswith("aws_") and resource_type not in {
        "aws_autoscaling_policy", "aws_iam_policy", "aws_iam_role_policy",
    }
    missing = sorted(REQUIRED_TAGS - tags)
    if taggable and missing:
        findings.append(_finding(
            file_name, resource_type, resource_name,
            issue_type="missing_tags",
            severity="low",
            description=f"Resource is missing these cost-allocation tags: {', '.join(missing)}.",
            recommendation="Add organization-approved ownership and cost-allocation tags.",
        ))
    return findings


def analyze_terraform_file(file_path: Path) -> list[dict]:
    try:
        with file_path.open(encoding="utf-8") as source:
            document = hcl2.load(source)
    except (OSError, ValueError, TypeError, UnexpectedInput) as exc:
        raise TerraformParseError(f"Unable to parse {file_path.name}: {exc}") from exc

    findings: list[dict] = []
    resource_types: set[str] = set()
    for resource_group in document.get("resource", []):
        for resource_type, named_resources in resource_group.items():
            resource_types.add(resource_type)
            for resource_name, attributes in named_resources.items():
                findings.extend(analyze_resource(file_path.name, resource_type, resource_name, attributes))

    if "aws_lb" in resource_types and "aws_autoscaling_group" not in resource_types:
        findings.append(_finding(
            file_path.name, "aws_lb", "load_balancer",
            issue_type="missing_autoscaling",
            severity="medium",
            description="A load balancer is declared without an Auto Scaling Group in the same file.",
            recommendation="Verify scaling is defined in another module or add an Auto Scaling Group and policy.",
        ))
    return findings


def _resolve_files(file_path: str | None) -> list[Path]:
    samples_dir = Path(settings.infra_samples_path).resolve()
    if not file_path:
        return sorted(samples_dir.glob("*.tf")) if samples_dir.exists() else []
    requested = Path(file_path)
    if requested.name != file_path or requested.suffix != ".tf":
        raise TerraformParseError("file_path must be a .tf file name without directory components")
    candidate = (samples_dir / requested).resolve()
    if candidate.parent != samples_dir:
        raise TerraformParseError("file_path resolves outside the configured samples directory")
    return [candidate] if samples_dir.exists() else []


def analyze_terraform(
    db: Session, file_path: str | None = None, persist: bool = True
) -> tuple[list[TerraformFinding], list[str]]:
    files = _resolve_files(file_path)
    if persist:
        query = db.query(TerraformFinding)
        if file_path:
            query = query.filter(TerraformFinding.file_name == file_path)
        query.delete(synchronize_session=False)

    all_findings: list[TerraformFinding] = []
    files_analyzed: list[str] = []
    try:
        for tf_file in files:
            if not tf_file.is_file():
                continue
            files_analyzed.append(tf_file.name)
            for values in analyze_terraform_file(tf_file):
                finding = TerraformFinding(**values)
                if persist:
                    db.add(finding)
                all_findings.append(finding)
        if persist:
            db.commit()
            for finding in all_findings:
                db.refresh(finding)
    except Exception:
        if persist:
            db.rollback()
        raise
    return all_findings, files_analyzed


def calculate_risk_score(findings: list[TerraformFinding]) -> int:
    weights = {"high": 30, "medium": 15, "low": 5}
    return min(100, sum(weights.get(finding.severity, 5) for finding in findings))
