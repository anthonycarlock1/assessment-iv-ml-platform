output "vpc_id" {
  description = "VPC created for the assessment platform"
  value       = aws_vpc.assessment.id
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster created for the assessment"
  value       = aws_eks_cluster.assessment.name
}

output "eks_cluster_endpoint" {
  description = "API endpoint for the EKS cluster"
  value       = aws_eks_cluster.assessment.endpoint
}

output "eks_cluster_certificate_authority" {
  description = "Cluster certificate authority data"
  value       = aws_eks_cluster.assessment.certificate_authority[0].data
  sensitive   = true
}

output "ecr_forecasting_repository" {
  description = "ECR repository for the forecasting service"
  value       = aws_ecr_repository.forecasting.repository_url
}

output "ecr_fraud_repository" {
  description = "ECR repository for the fraud service"
  value       = aws_ecr_repository.fraud.repository_url
}

output "ecr_recommendations_repository" {
  description = "ECR repository for the recommendations service"
  value       = aws_ecr_repository.recommendations.repository_url
}

output "student_eks_principal" {
  description = "IAM principal granted EKS access, if configured"
  value       = var.student_iam_arn != "" ? aws_eks_access_entry.student[0].principal_arn : null
}