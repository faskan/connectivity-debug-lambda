data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  filter {
    name   = "tag:my-vpc-id"
    values = ["primary-vpc"]
  }
}

data "aws_subnets" "public" {
  tags = {
    "telenet.be:foundation:networking:id" = "primary-vpc:public"
  }
}

data "aws_subnets" "private" {
  tags = {
    "telenet.be:foundation:networking:id" = "primary-vpc:private"
  }
}
data "aws_subnets" "workload" {
  tags = {
    "telenet.be:foundation:networking:id" = "primary-vpc:workload"
  }
}
