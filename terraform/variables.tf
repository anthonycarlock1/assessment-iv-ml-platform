variable "aws_region" {
  description = "AWS region for the Assessment IV platform"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for all AWS resources"
  type        = string
  default     = "anthony-assessment4"
}

variable "owner" {
  description = "Owner name appended to resource names and tags"
  type        = string
  default     = "anthony"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster to create for this assessment"
  type        = string
  default     = "assessment4-eks"
}

variable "eks_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.30"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.10.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets"
  type        = list(string)
  default     = ["10.10.1.0/24", "10.10.2.0/24"]
}

variable "node_instance_type" {
  description = "EC2 instance type for the EKS managed node group"
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 3
}

variable "student_iam_arn" {
  description = "Optional IAM principal to grant EKS admin access; leave blank to skip"
  type        = string
  default     = ""
}