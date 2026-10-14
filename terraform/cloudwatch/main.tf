# Independent state avoids applying unrelated EKS foundation changes.
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
provider "aws" {
  region = "us-east-1"
}
locals {
  cluster  = "anthony-assessment4-eks"
  prefix   = "anthony-assessment4"
  tags     = { Owner = "anthony", Project = "anthony-assessment4", ManagedBy = "Terraform" }
  services = toset(["fraud", "forecasting", "recommendations"])
  log_groups = toset([
    "/aws/containerinsights/anthony-assessment4-eks/application",
    "/aws/containerinsights/anthony-assessment4-eks/dataplane",
    "/aws/containerinsights/anthony-assessment4-eks/host",
    "/aws/containerinsights/anthony-assessment4-eks/performance",
    "/aws/eks/anthony-assessment4-eks/cluster",
  ])
}
resource "aws_cloudwatch_log_group" "cluster" {
  for_each          = local.log_groups
  name              = each.value
  retention_in_days = 14
  skip_destroy      = true
  tags              = local.tags
}
resource "aws_iam_role" "collector" {
  name = "${local.prefix}-cloudwatch-collector"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "pods.eks.amazonaws.com" }
      Action    = ["sts:AssumeRole", "sts:TagSession"]
      Condition = { StringEquals = {
        "aws:RequestTag/eks-cluster-name"           = local.cluster
        "aws:RequestTag/kubernetes-namespace"       = "amazon-cloudwatch"
        "aws:RequestTag/kubernetes-service-account" = "cloudwatch-agent"
      } }
    }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "collector" {
  role       = aws_iam_role.collector.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}
resource "aws_eks_addon" "cloudwatch" {
  cluster_name  = local.cluster
  addon_name    = "amazon-cloudwatch-observability"
  addon_version = "v6.7.0-eksbuild.1"
  configuration_values = jsonencode({
    applicationSignals    = { enabled = false }
    manager               = { applicationSignals = { autoMonitor = { monitorAllServices = false, restartPods = false } } }
    containerLogs         = { enabled = true }
    containerInsights     = { enabled = true }
    otelContainerInsights = { enabled = false }
  })
  pod_identity_association {
    service_account = "cloudwatch-agent"
    role_arn        = aws_iam_role.collector.arn
  }
  depends_on = [aws_iam_role_policy_attachment.collector, aws_cloudwatch_log_group.cluster]
  tags       = local.tags
}
resource "aws_sns_topic" "alarms" {
  name = "${local.prefix}-cloudwatch-alarms"
  tags = local.tags
}

resource "aws_sns_topic_subscription" "alarm_email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = "anthonycarlock1@gmail.com"
}
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "${local.prefix}-api-errors"
  log_group_name = "/aws/containerinsights/${local.cluster}/application"
  pattern        = "{ $.log_processed.status >= 500 }"
  metric_transformation {
    name          = "Api5xxErrors"
    namespace     = "Anthony/Assessment4"
    value         = "1"
    default_value = 0
  }
  depends_on = [aws_cloudwatch_log_group.cluster]
}
resource "aws_cloudwatch_log_metric_filter" "history_errors" {
  name           = "${local.prefix}-history-write-errors"
  log_group_name = "/aws/containerinsights/${local.cluster}/application"
  pattern        = "{ $.log_processed.event = \"prediction_history_write_failed\" }"
  metric_transformation {
    name          = "HistoryWriteErrors"
    namespace     = "Anthony/Assessment4"
    value         = "1"
    default_value = 0
  }
  depends_on = [aws_cloudwatch_log_group.cluster]
}
resource "aws_cloudwatch_metric_alarm" "api_errors" {
  for_each            = toset(["Api5xxErrors", "HistoryWriteErrors"])
  alarm_name          = "${local.prefix}-${each.key}"
  alarm_description   = "Application log error events; inspect project CloudWatch application logs."
  namespace           = "Anthony/Assessment4"
  metric_name         = each.key
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  tags                = local.tags
}
resource "aws_cloudwatch_metric_alarm" "sagemaker_errors" {
  for_each            = local.services
  alarm_name          = "${local.prefix}-${each.key}-sagemaker-5xx"
  alarm_description   = "SageMaker endpoint returned server errors. Check hosting logs and cold-start availability."
  namespace           = "AWS/SageMaker"
  metric_name         = "Invocation5XXErrors"
  dimensions          = { EndpointName = "${local.prefix}-${each.key}-sagemaker", VariantName = "AllTraffic" }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  tags                = local.tags
}
resource "aws_cloudwatch_metric_alarm" "sagemaker_latency" {
  for_each            = local.services
  alarm_name          = "${local.prefix}-${each.key}-sagemaker-latency"
  alarm_description   = "Average model latency exceeds 5 seconds for two minutes (metric is microseconds)."
  namespace           = "AWS/SageMaker"
  metric_name         = "ModelLatency"
  dimensions          = { EndpointName = "${local.prefix}-${each.key}-sagemaker", VariantName = "AllTraffic" }
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 2
  threshold           = 5000000
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  tags                = local.tags
}
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttles" {
  for_each            = toset(["ReadThrottleEvents", "WriteThrottleEvents"])
  alarm_name          = "${local.prefix}-dynamodb-${each.key}"
  alarm_description   = "Prediction-history DynamoDB requests are throttled."
  namespace           = "AWS/DynamoDB"
  metric_name         = each.key
  dimensions          = { TableName = "${local.prefix}-prediction-history" }
  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  tags                = local.tags
}
resource "aws_cloudwatch_metric_alarm" "node_utilization" {
  for_each            = toset(["node_cpu_utilization", "node_memory_utilization"])
  alarm_name          = "${local.prefix}-${each.key}"
  alarm_description   = "Cluster average node utilization exceeds 80 percent for three minutes."
  namespace           = "ContainerInsights"
  metric_name         = each.key
  dimensions          = { ClusterName = local.cluster }
  statistic           = "Average"
  period              = 60
  evaluation_periods  = 3
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]
  tags                = local.tags
}
resource "aws_cloudwatch_dashboard" "project" {
  dashboard_name = "${local.prefix}-operations"
  dashboard_body = file("${path.module}/dashboard.json")
}
output "dashboard_url" {
  value = "https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/${aws_cloudwatch_dashboard.project.dashboard_name}"
}
output "alarm_topic_arn" {
  value = aws_sns_topic.alarms.arn
}
