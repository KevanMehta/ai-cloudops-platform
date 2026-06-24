resource "aws_s3_bucket" "public_assets" {
  bucket = "company-public-assets"
  acl    = "public-read"

  tags = {
    Environment = "production"
  }
}

resource "aws_s3_bucket" "backups" {
  bucket = "company-backups-unencrypted"

  tags = {
    Environment = "production"
    Team        = "data"
  }
}

resource "aws_s3_bucket" "logs" {
  bucket = "company-logs-bucket"
}
