import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import TerraformFinding

logger = logging.getLogger(__name__)

RESOURCE_PATTERN = re.compile(
    r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
    re.DOTALL,
)

INSTANCE_TYPES = {
    "m5.4xlarge": "high",
    "m5.2xlarge": "medium",
    "r5.4xlarge": "high",
    "p3.2xlarge": "high",
}


def _get_attr(block: str, attr: str) -> str | None:
    match = re.search(rf'{attr}\s*=\s*"([^"]+)"', block)
    if match:
        return match.group(1)
    match = re.search(rf"{attr}\s*=\s*(true|false|\d+)", block)
    return match.group(1) if match else None


def _has_tags(block: str) -> bool:
    return "tags" in block and ("Environment" in block or "Team" in block)


def analyze_block(file_name: str, resource_type: str, resource_name: str, block: str) -> list[dict]:
    findings: list[dict] = []

    if resource_type == "aws_instance":
        instance_type = _get_attr(block, "instance_type") or ""
        if instance_type in INSTANCE_TYPES or "xlarge" in instance_type:
            findings.append(
                {
                    "file_name": file_name,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "issue_type": "overprovisioned_instance",
                    "severity": INSTANCE_TYPES.get(instance_type, "medium"),
                    "description": f"Instance type {instance_type} may be overprovisioned for typical workloads.",
                    "recommendation": "Right-size to m5.large or m5.xlarge based on CloudWatch CPU/memory metrics.",
                }
            )
        if not _has_tags(block):
            findings.append(
                {
                    "file_name": file_name,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "issue_type": "missing_tags",
                    "severity": "low",
                    "description": f"EC2 instance '{resource_name}' is missing cost allocation tags.",
                    "recommendation": "Add tags: Environment, Team, CostCenter, ManagedBy.",
                }
            )

    if resource_type == "aws_s3_bucket":
        acl = _get_attr(block, "acl")
        if acl == "public-read" or "public" in block.lower():
            findings.append(
                {
                    "file_name": file_name,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "issue_type": "public_storage",
                    "severity": "high",
                    "description": f"S3 bucket '{resource_name}' may allow public access.",
                    "recommendation": "Enable Block Public Access and use CloudFront with OAI for public content.",
                }
            )
        if not _has_tags(block):
            findings.append(
                {
                    "file_name": file_name,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "issue_type": "missing_tags",
                    "severity": "low",
                    "description": f"S3 bucket '{resource_name}' lacks required tags.",
                    "recommendation": "Add cost allocation tags for chargeback reporting.",
                }
            )

    if resource_type == "aws_db_instance":
        instance_class = _get_attr(block, "instance_class") or ""
        if "xlarge" in instance_class or "2xlarge" in instance_class:
            findings.append(
                {
                    "file_name": file_name,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "issue_type": "overprovisioned_instance",
                    "severity": "medium",
                    "description": f"RDS instance class {instance_class} may exceed workload requirements.",
                    "recommendation": "Review Performance Insights and consider db.r5.large with read replicas.",
                }
            )

    if resource_type == "aws_autoscaling_group":
        min_size = _get_attr(block, "min_size")
        max_size = _get_attr(block, "max_size")
        if min_size and max_size and min_size == max_size:
            findings.append(
                {
                    "file_name": file_name,
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "issue_type": "missing_autoscaling",
                    "severity": "medium",
                    "description": f"ASG '{resource_name}' has fixed capacity (min=max={min_size}).",
                    "recommendation": "Configure dynamic scaling with target tracking on CPU utilization.",
                }
            )

    return findings


def analyze_terraform_file(file_path: Path) -> list[dict]:
    content = file_path.read_text(encoding="utf-8")
    file_name = file_path.name
    all_findings: list[dict] = []

    for match in RESOURCE_PATTERN.finditer(content):
        resource_type, resource_name, block = match.groups()
        all_findings.extend(analyze_block(file_name, resource_type, resource_name, block))

    # Detect missing autoscaling when EC2/ALB exists without ASG
    if "aws_lb" in content and "aws_autoscaling_group" not in content:
        all_findings.append(
            {
                "file_name": file_name,
                "resource_type": "aws_lb",
                "resource_name": "load_balancer",
                "issue_type": "missing_autoscaling",
                "severity": "medium",
                "description": "Load balancer defined without associated Auto Scaling Group.",
                "recommendation": "Add ASG with target tracking scaling policy behind the ALB.",
            }
        )

    return all_findings


def analyze_terraform(
    db: Session, file_path: str | None = None, persist: bool = True
) -> tuple[list[TerraformFinding], list[str]]:
    samples_dir = Path(settings.infra_samples_path)
    if not samples_dir.exists():
        logger.warning("Infra samples path not found: %s", samples_dir)
        return [], []

    if file_path:
        files = [samples_dir / file_path]
    else:
        files = sorted(samples_dir.glob("*.tf"))

    if persist:
        if file_path:
            db.query(TerraformFinding).filter(
                TerraformFinding.file_name == file_path
            ).delete()
        else:
            db.query(TerraformFinding).delete()
        db.commit()

    all_findings: list[TerraformFinding] = []
    files_analyzed: list[str] = []

    for tf_file in files:
        if not tf_file.exists():
            continue
        files_analyzed.append(tf_file.name)
        raw_findings = analyze_terraform_file(tf_file)
        for f in raw_findings:
            finding = TerraformFinding(**f)
            if persist:
                db.add(finding)
            all_findings.append(finding)

    if persist and all_findings:
        db.commit()
        for f in all_findings:
            db.refresh(f)

    return all_findings, files_analyzed


def calculate_risk_score(findings: list[TerraformFinding]) -> int:
    weights = {"high": 30, "medium": 15, "low": 5}
    score = sum(weights.get(f.severity, 5) for f in findings)
    return min(100, score)
