# Sets the minimum Terraform version and compatible AWS-provider version.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Configures the AWS provider with the input region.
provider "aws" {
  region = var.aws_region
}