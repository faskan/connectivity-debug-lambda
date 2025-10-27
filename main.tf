variable "lambda_memory_size" {
  type    = number
  default = 256
}

resource "aws_security_group" "lambda_sg" {

  name        = "debug-lambda-sg"
  description = "Security group for debug lambda"
  vpc_id      = data.aws_vpc.default.id
  egress {
    description      = "Allow all outbound IPv4 traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
  }

  egress {
    description      = "Allow all outbound IPv6 traffic"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = []
    ipv6_cidr_blocks = ["::/0"]
  }
}



############################################
# Lambda
############################################
module "main_lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~>7.20"

  function_name                     = "debug-lambda"
  description                       = "debug lambda"
  handler                           = "debug_lambda.handler"
  runtime                           = "python3.12"
  timeout                           = 10
  memory_size                       = var.lambda_memory_size
  source_path                       = "${path.module}/lambda"
  vpc_subnet_ids                    = data.aws_subnets.workload.ids
  vpc_security_group_ids            = [aws_security_group.lambda_sg.id]
  cloudwatch_logs_retention_in_days = 1

  publish = true

  # XRay tracing
  tracing_mode          = "Active"
  attach_tracing_policy = true

  attach_policy_statements = true
  policy_statements = {
    VPCNetworking = {
      effect = "Allow"
      actions = [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ]
      resources = ["*"]
    }
  }
}
