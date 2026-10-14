# This Terraform file creates the AWS foundation for the project.
# In simple terms: it builds the network, the cluster, and the container registry.
# If you are explaining it in a presentation, think of this as the "cloud setup" layer.

# Finds available AWS zones.
data "aws_availability_zones" "available" {
  state = "available"
}

# These are shared values used on many AWS resources.
# Example: every resource gets a project name, environment, and owner tag.
# Selects two zones and builds shared project/environment/owner tags.
locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "Terraform"
  }
}

# Create the private network in AWS.
# This is like creating the office building foundation for all services.
# Creates the project network, enables DNS, and adds ownership tags.
resource "aws_vpc" "assessment" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-vpc"
  })
}

# The internet gateway lets resources in the VPC talk to the internet.
# Provides an internet route for the public subnets.
resource "aws_internet_gateway" "assessment" {
  vpc_id = aws_vpc.assessment.id

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-igw"
  })
}

# Subnets are like separate rooms inside the network.
# We create public subnets so EKS nodes can be reached from the internet.
# Builds public subnets/routing across the selected zones.
resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.assessment.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name                                                         = "${var.owner}-${var.project_name}-public-${count.index + 1}"
    "kubernetes.io/cluster/${var.owner}-${var.eks_cluster_name}" = "shared"
    "kubernetes.io/role/elb"                                     = "1"
  })
}

# Route table tells the VPC how to send traffic.
# Here, we send all traffic to the internet gateway.
# Routes internet-bound traffic through the internet gateway.
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.assessment.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.assessment.id
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-public-rt"
  })
}

# Connects each public subnet to that route table.
resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security groups act like firewall rules.
# They define what traffic is allowed in and out.
# Defines cluster firewall rules: HTTPS ingress and outbound traffic; these rules do not replace
# AWS authentication.
resource "aws_security_group" "cluster" {
  # We keep the safe name format so Terraform does not replace it unnecessarily.
  name        = "${var.project_name}-eks-cluster-sg"
  description = "Security group for the Assessment IV EKS cluster"
  vpc_id      = aws_vpc.assessment.id

  # Define permitted outbound network traffic.
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Define permitted inbound network traffic.
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-eks-cluster-sg"
  })
}

# IAM role for the EKS cluster itself.
# This gives AWS permission to manage the cluster.
# Configures cluster networking or its AWS management role.
resource "aws_iam_role" "cluster" {
  name = "${var.owner}-${var.project_name}-eks-cluster-role"

  # Define which AWS service may assume this IAM role.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-eks-cluster-role"
  })
}

# Attaches the AWS EKS cluster-management policy.
resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

# This is the main Kubernetes cluster.
# EKS is the managed Kubernetes service from AWS.
# Creates/configures the managed EKS control plane, including version, subnet placement, public
# API endpoint, and role dependency.
resource "aws_eks_cluster" "assessment" {
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  name                      = "${var.owner}-${var.eks_cluster_name}"
  role_arn                  = aws_iam_role.cluster.arn
  version                   = var.eks_version

  # Set cluster subnets, firewall groups, and API endpoint access.
  vpc_config {
    subnet_ids             = aws_subnet.public[*].id
    security_group_ids     = [aws_security_group.cluster.id]
    endpoint_public_access = true
    public_access_cidrs    = ["0.0.0.0/0"]
  }

  # Wait for these AWS dependencies before creating this resource.
  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy
  ]

  tags = merge(local.common_tags, {
    Name  = "${var.owner}-${var.eks_cluster_name}",
    Owner = var.owner
  })
}

# IAM role for the worker nodes in the EKS cluster.
# These nodes run our Docker containers.
# Defines the EC2 worker-role trust.
resource "aws_iam_role" "node_group" {
  name = "${var.owner}-${var.project_name}-eks-node-role"

  # Define which AWS service may assume this IAM role.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-eks-node-role"
  })
}

# Attach the AWS policies needed for EKS worker nodes.
# Gives nodes the EKS worker permissions.
resource "aws_iam_role_policy_attachment" "node_group_eks_worker" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node_group.name
}

# Gives the network plugin permissions needed for pod networking.
resource "aws_iam_role_policy_attachment" "node_group_eks_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node_group.name
}

# Lets nodes pull container images from ECR.
resource "aws_iam_role_policy_attachment" "node_group_ecr_readonly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node_group.name
}

# This creates the EC2 machines that run Kubernetes workloads.
# Defines worker-machine type, scaling range, and rolling-update settings.
resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.assessment.name
  node_group_name = "${var.owner}-${var.project_name}-ng"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = aws_subnet.public[*].id
  instance_types  = [var.node_instance_type]
  ami_type        = var.node_ami_type
  capacity_type   = "ON_DEMAND"

  # Set desired, minimum, and maximum worker-machine counts.
  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  # Limit how many workers can be unavailable during an update.
  update_config {
    max_unavailable = 1
  }

  # Wait for these AWS dependencies before creating this resource.
  depends_on = [
    aws_iam_role_policy_attachment.node_group_eks_worker,
    aws_iam_role_policy_attachment.node_group_eks_cni,
    aws_iam_role_policy_attachment.node_group_ecr_readonly,
    aws_eks_cluster.assessment
  ]

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-eks-node-group"
  })
}

# Optional IAM access so a user can manage the cluster.
# Optionally creates an EKS access entry for the configured principal.
resource "aws_eks_access_entry" "student" {
  count = var.student_iam_arn != "" ? 1 : 0

  cluster_name  = aws_eks_cluster.assessment.name
  principal_arn = var.student_iam_arn
  type          = "STANDARD"
}

# Optionally grants cluster-admin access to that principal.
resource "aws_eks_access_policy_association" "student_cluster_admin" {
  count = var.student_iam_arn != "" ? 1 : 0

  cluster_name  = aws_eks_cluster.assessment.name
  principal_arn = aws_eks_access_entry.student[0].principal_arn

  policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  # Set the scope of the configured Kubernetes access grant.
  access_scope {
    type = "cluster"
  }
}

# ECR is AWS's container registry.
# We store each app image here before deploying it to Kubernetes.
# Defines the forecasting ECR repository. Enables image scanning, allows mutable tags, and permits
# deleting a nonempty repository when Terraform destroys it (force_delete).
resource "aws_ecr_repository" "forecasting" {
  name                 = "${var.owner}-assessment4-forecasting"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  # Scan uploaded images for known vulnerabilities.
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-assessment4-forecasting"
  })
}

# Defines the fraud ECR repository. Enables image scanning, allows mutable tags, and permits
# deleting a nonempty repository when Terraform destroys it (force_delete).
resource "aws_ecr_repository" "fraud" {
  name                 = "${var.owner}-assessment4-fraud"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  # Scan uploaded images for known vulnerabilities.
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-assessment4-fraud"
  })
}

# Defines the recommendations ECR repository. Enables image scanning, allows mutable tags, and
# permits deleting a nonempty repository when Terraform destroys it (force_delete).
resource "aws_ecr_repository" "recommendations" {
  name                 = "${var.owner}-assessment4-recommendations"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  # Scan uploaded images for known vulnerabilities.
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-assessment4-recommendations"
  })
}
