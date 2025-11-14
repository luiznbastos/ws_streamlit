variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "stage" {
  description = "Environment stage (stg, prod)"
  type        = string
  default     = "stg"
}

variable "my_ip" {
  description = "IP address for SSH access"
  type        = string
  default     = "177.75.55.218/32"
}

variable "docker_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "key_pair_name" {
  description = "AWS key pair name"
  type        = string
  default     = "streamlit-app-key-pair"

  validation {
    condition     = trimspace(var.key_pair_name) != ""
    error_message = "Key pair name cannot be empty or contain only whitespace."
  }
}

variable "assume_role_arn" {
  description = "ARN of the role to assume for AWS operations"
  type        = string
}

locals {
  app_name = var.stage == "prod" ? "streamlit-app" : "streamlit-app-${var.stage}"

  # Clean key pair name removing any whitespace
  clean_key_pair_name = trimspace(var.key_pair_name)

  common_tags = {
    Environment = var.stage
    Project     = local.app_name
    ManagedBy   = "terraform"
  }
} 