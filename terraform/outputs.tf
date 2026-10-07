# Exports vpc id for operators or other tooling.
output "vpc_id" {
  description = "VPC created for the assessment platform"
  value       = aws_vpc.assessment.id
}

# Exports eks cluster name for operators or other tooling.
output "eks_cluster_name" {
  description = "Name of the EKS cluster created for the assessment"
  value       = aws_eks_cluster.assessment.name
}

# Exports eks cluster endpoint for operators or other tooling.
output "eks_cluster_endpoint" {
  description = "API endpoint for the EKS cluster"
  value       = aws_eks_cluster.assessment.endpoint
}

# Exports eks cluster certificate authority for operators or other tooling. Terraform marks this
# output sensitive.
output "eks_cluster_certificate_authority" {
  description = "Cluster certificate authority data"
  value       = aws_eks_cluster.assessment.certificate_authority[0].data
  sensitive   = true
}

# Exports ecr forecasting repository for operators or other tooling.
output "ecr_forecasting_repository" {
  description = "ECR repository for the forecasting service"
  value       = aws_ecr_repository.forecasting.repository_url
}

# Exports ecr fraud repository for operators or other tooling.
output "ecr_fraud_repository" {
  description = "ECR repository for the fraud service"
  value       = aws_ecr_repository.fraud.repository_url
}

# Exports ecr recommendations repository for operators or other tooling.
output "ecr_recommendations_repository" {
  description = "ECR repository for the recommendations service"
  value       = aws_ecr_repository.recommendations.repository_url
}

# Exports student eks principal for operators or other tooling.
output "student_eks_principal" {
  description = "IAM principal granted EKS access, if configured"
  value       = var.student_iam_arn != "" ? aws_eks_access_entry.student[0].principal_arn : null
}