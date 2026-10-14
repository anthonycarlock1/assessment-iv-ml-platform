# Separate Terraform state keeps storage changes independent of the EKS foundation.
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
  roles = {
    fraud           = "anthony-assessment4-fraud-invoke"
    forecasting     = "anthony-assessment4-forecasting-invoke-v2"
    recommendations = "anthony-assessment4-recommendations-invoke-v2"
  }
}

resource "aws_dynamodb_table" "prediction_history" {
  name         = "anthony-assessment4-prediction-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "service"
  range_key    = "event_id"

  attribute {
    name = "service"
    type = "S"
  }
  attribute {
    name = "event_id"
    type = "S"
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  server_side_encryption {
    enabled = true
  }
  point_in_time_recovery {
    enabled = true
  }
  tags = {
    Owner     = "anthony"
    Project   = "anthony-assessment4"
    ManagedBy = "Terraform"
  }
}

# Separate policy leaves existing SageMaker invocation permissions unchanged.
resource "aws_iam_role_policy" "prediction_history" {
  for_each = local.roles
  name     = "assessment4-prediction-history"
  role     = each.value
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:Query"]
      Resource = aws_dynamodb_table.prediction_history.arn
      Condition = {
        "ForAllValues:StringEquals" = { "dynamodb:LeadingKeys" = [each.key] }
      }
    }]
  })
}

output "prediction_history_table" {
  value = aws_dynamodb_table.prediction_history.name
}
