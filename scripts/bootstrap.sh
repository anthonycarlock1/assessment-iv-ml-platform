#!/usr/bin/env bash
set -euo pipefail
# Selects the intended region and existing cluster.
AWS_REGION="${AWS_REGION:-us-east-1}"
EKS_CLUSTER_NAME="${EKS_CLUSTER_NAME:-anthony-assessment4-eks}"
# Shows which AWS account/identity the CLI is using.
aws sts get-caller-identity --region "$AWS_REGION"
# Reads cluster name/status/version without making changes.
aws eks describe-cluster --name "$EKS_CLUSTER_NAME" --region "$AWS_REGION" --query 'cluster.{name:name,status:status,version:version}'
echo "Read-only validation complete. Use scripts/deploy.sh after building and testing."
