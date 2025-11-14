# EC2 Instance
resource "aws_instance" "app_server" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  key_name                    = local.clean_key_pair_name
  subnet_id                   = data.aws_subnets.public.ids[0]
  associate_public_ip_address = true
  vpc_security_group_ids      = [local.security_group_id]
  iam_instance_profile        = local.instance_profile_name
  disable_api_termination     = true

  root_block_device {
    volume_size           = 8
    volume_type           = "gp3"
    delete_on_termination = true
    encrypted             = true
  }

  user_data = <<-EOF
              #!/bin/bash
              set -e

              # Log all output
              exec > >(tee /var/log/user-data.log) 2>&1

              echo "Starting user data script..."

              # Update system
              dnf update -y

              # Install Docker
              dnf install -y docker
              systemctl start docker
              systemctl enable docker
              usermod -a -G docker ec2-user

              # Install AWS CLI v2
              curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
              unzip awscliv2.zip
              ./aws/install
              rm -rf aws awscliv2.zip

              echo "User data script completed successfully"
              EOF

  tags = merge(local.common_tags, {
    Name = "${local.app_name}-server"
  })

  lifecycle {
    create_before_destroy = true
  }
}