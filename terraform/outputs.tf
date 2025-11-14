output "public_ip" {
  description = "Public IP of the EC2 instance"
  value       = aws_instance.app_server.public_ip
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.app_server.id
}

output "ecr_repository_url" {
  description = "ECR repository URL"
  value       = local.ecr_repository_url
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${aws_instance.app_server.public_ip}:8501"
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_instance.app_server.public_ip}"
} 