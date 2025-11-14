# Main configuration file - imports all modules
# This file serves as the entry point for the Terraform configuration

# All provider configurations are in provider.tf
# All variables are defined in variables.tf
# All data sources are in data.tf
# ECR resources are in ecr.tf
# Security resources (SG, IAM) are in security.tf
# Compute resources (EC2) are in compute.tf
# All outputs are in outputs.tf

locals {
  stage      = lower(var.stage)
  is_prod    = local.stage == "prod" ? true : false
  env_suffix = local.is_prod ? "" : "-${local.stage}"
}

terraform {
  backend "s3" {
    bucket  = "tf-document-transformer"
    key     = "streamlit/terraform.tfstate"
    region  = "us-east-1"
    profile = "default"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.58"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "default"
  assume_role {
    role_arn = var.assume_role_arn
  }
}