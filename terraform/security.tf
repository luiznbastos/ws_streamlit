# Security Group
resource "aws_security_group" "app_sg" {
  name        = "${local.app_name}-sg"
  description = "Security group for ${local.app_name}"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  ingress {
    description = "Streamlit"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Port 8000 from your IP"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.app_name}-sg"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# IAM Role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "${local.app_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# IAM Policy for ECR access
resource "aws_iam_role_policy" "ecr_policy" {
  name = "${local.app_name}-ecr-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = ["*"]
      }
    ]
  })
}

# IAM Policy for Redshift access
resource "aws_iam_role_policy" "redshift_policy" {
  name = "${local.app_name}-redshift-policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "redshift:GetClusterCredentials",
          "redshift:DescribeClusters",
          "redshift-serverless:GetCredentials",
          "redshift-serverless:GetWorkgroup"
        ]
        Resource = ["*"]
      }
    ]
  })
}

# Instance Profile
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${local.app_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name

  tags = local.common_tags
}

# Locals to get the correct resources
locals {
  security_group_id     = aws_security_group.app_sg.id
  iam_role_arn          = aws_iam_role.ec2_role.arn
  instance_profile_name = aws_iam_instance_profile.ec2_profile.name
} 