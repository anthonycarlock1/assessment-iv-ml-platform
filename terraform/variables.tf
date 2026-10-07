# This file holds the settings for the cloud environment.
# Think of these as the configuration values we pass into Terraform.
# A beginner-friendly way to understand this: these are the "inputs".

# Chooses the AWS region for infrastructure.
variable "aws_region" {
  description = "AWS region for the Assessment IV platform"
  type        = string
  default     = "us-east-1"
}

# Sets the project label/name used by resources.
variable "project_name" {
  description = "Project name used for all AWS resources"
  type        = string
  default     = "anthony-assessment4"
}

# Sets the owner name used in resource names and tags.
variable "owner" {
  description = "Owner name appended to resource names and tags"
  type        = string
  default     = "anthony"
}

# Labels the environment, such as dev.
variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

# Supplies the cluster-name suffix; main.tf adds the owner prefix.
variable "eks_cluster_name" {
  description = "Name of the EKS cluster to create for this assessment"
  type        = string
  default     = "assessment4-eks"
}

# Pins the cluster Kubernetes version.
variable "eks_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  # This version is pinned to avoid a bad version downgrade or mismatch.
  default = "1.31"
}

# Defines the network address range.
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.10.0.0/16"
}

# Defines the address ranges for public subnets.
variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets"
  type        = list(string)
  default     = ["10.10.1.0/24", "10.10.2.0/24"]
}

# Chooses the worker-machine type.
variable "node_instance_type" {
  description = "EC2 instance type for the EKS managed node group"
  type        = string
  default     = "t3.medium"
}

# Keep the live node image unchanged; the rebuild runbook selects AL2023 explicitly.
variable "node_ami_type" {
  description = "EKS managed-node AMI type; use AL2023_x86_64_STANDARD for a fresh rebuild"
  type        = string
  default     = "AL2_x86_64"
}

# Sets the normal desired worker count.
variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

# Sets the minimum worker count.
variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

# Sets the maximum worker count.
variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 3
}

# Optionally identifies the AWS principal granted cluster-admin access; an empty value skips that
# grant.
variable "student_iam_arn" {
  description = "Optional IAM principal to grant EKS admin access; leave blank to skip"
  type        = string
  default     = ""
}
