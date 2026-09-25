data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = var.owner
    ManagedBy   = "Terraform"
  }
}

resource "aws_vpc" "assessment" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-vpc"
  })
}

resource "aws_internet_gateway" "assessment" {
  vpc_id = aws_vpc.assessment.id

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-igw"
  })
}

resource "aws_subnet" "public" {
  count                   = length(local.azs)
  vpc_id                  = aws_vpc.assessment.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-public-${count.index + 1}"
    "kubernetes.io/cluster/${var.owner}-${var.eks_cluster_name}" = "shared"
    "kubernetes.io/role/elb" = "1"
  })
}

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

resource "aws_route_table_association" "public" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "cluster" {
  name        = "${var.owner}-${var.project_name}-eks-cluster-sg"
  description = "Security group for the Assessment IV EKS cluster"
  vpc_id      = aws_vpc.assessment.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.project_name}-eks-cluster-sg"
  })
}

resource "aws_iam_role" "cluster" {
  name = "${var.owner}-${var.project_name}-eks-cluster-role"

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

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_eks_cluster" "assessment" {
  name     = "${var.owner}-${var.eks_cluster_name}"
  role_arn = aws_iam_role.cluster.arn
  version  = var.eks_version

  vpc_config {
    subnet_ids              = aws_subnet.public[*].id
    security_group_ids      = [aws_security_group.cluster.id]
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy
  ]

  tags = merge(local.common_tags, {
    Name = "${var.owner}-${var.eks_cluster_name}",
    Owner = var.owner
  })
}

resource "aws_iam_role" "node_group" {
  name = "${var.owner}-${var.project_name}-eks-node-role"

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

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "node_group_eks_worker" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_eks_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_ecr_readonly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node_group.name
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.assessment.name
  node_group_name = "${var.owner}-${var.project_name}-ng"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = aws_subnet.public[*].id
  instance_types  = [var.node_instance_type]
  ami_type        = "AL2_x86_64"
  capacity_type   = "ON_DEMAND"

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    max_unavailable = 1
  }

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

resource "aws_eks_access_entry" "student" {
  count = var.student_iam_arn != "" ? 1 : 0

  cluster_name  = aws_eks_cluster.assessment.name
  principal_arn = var.student_iam_arn
  type          = "STANDARD"
}

resource "aws_eks_access_policy_association" "student_cluster_admin" {
  count = var.student_iam_arn != "" ? 1 : 0

  cluster_name  = aws_eks_cluster.assessment.name
  principal_arn = aws_eks_access_entry.student[0].principal_arn

  policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }
}

resource "aws_ecr_repository" "forecasting" {
  name                 = "${var.owner}-assessment4-forecasting"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-assessment4-forecasting"
  })
}

resource "aws_ecr_repository" "fraud" {
  name                 = "${var.owner}-assessment4-fraud"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-assessment4-fraud"
  })
}

resource "aws_ecr_repository" "recommendations" {
  name                 = "${var.owner}-assessment4-recommendations"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.owner}-assessment4-recommendations"
  })
}
