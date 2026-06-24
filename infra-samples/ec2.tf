resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "m5.4xlarge"

  tags = {
    Name = "web-server"
  }
}

resource "aws_instance" "api_server" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "m5.2xlarge"
}

resource "aws_lb" "main" {
  name               = "production-alb"
  internal           = false
  load_balancer_type = "application"

  tags = {
    Environment = "production"
    Team        = "platform"
  }
}
