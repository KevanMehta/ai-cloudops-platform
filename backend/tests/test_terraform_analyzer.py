from pathlib import Path

import pytest

from app.services.terraform_analyzer import TerraformParseError, analyze_terraform_file, _resolve_files


def test_hcl_parser_finds_public_bucket_and_missing_tags(tmp_path: Path):
    terraform = tmp_path / "storage.tf"
    terraform.write_text('''
resource "aws_s3_bucket" "assets" {
  bucket = "example-assets"
  acl    = "public-read"
  tags = { Environment = "test" }
}
''', encoding="utf-8")

    findings = analyze_terraform_file(terraform)
    issue_types = {finding["issue_type"] for finding in findings}
    assert issue_types == {"public_storage", "missing_tags"}


def test_hcl_parser_reports_invalid_input(tmp_path: Path):
    terraform = tmp_path / "invalid.tf"
    terraform.write_text('resource "aws_s3_bucket" "broken" {', encoding="utf-8")
    with pytest.raises(TerraformParseError, match="Unable to parse"):
        analyze_terraform_file(terraform)


@pytest.mark.parametrize("path", ["../secret.tf", "/tmp/secret.tf", "notes.txt", "nested/main.tf"])
def test_resolve_files_rejects_path_traversal(path):
    with pytest.raises(TerraformParseError, match="file_path"):
        _resolve_files(path)
