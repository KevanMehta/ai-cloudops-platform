resource "aws_db_instance" "primary" {
  identifier     = "production-db"
  engine         = "postgres"
  instance_class = "db.r5.2xlarge"
  allocated_storage = 500

  tags = {
    Environment = "production"
    Team        = "backend"
  }
}

resource "aws_eks_cluster" "main" {
  name     = "production-eks"
  role_arn = "arn:aws:iam::123456789012:role/eks-cluster"

  tags = {
    Environment = "production"
    Team        = "platform"
    CostCenter  = "engineering"
  }
}

resource "aws_autoscaling_group" "fixed_capacity" {
  name             = "web-asg"
  min_size         = 4
  max_size         = 4
  desired_capacity = 4

  tags = {
    Environment = "production"
  }
}
