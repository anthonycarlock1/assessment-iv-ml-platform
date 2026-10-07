#!/usr/bin/env bash
# Stops on command errors, missing variables, or failed pipelines.
set -euo pipefail
cd "$(dirname "$0")/.."
IMAGE_TAG="${IMAGE_TAG:?Set IMAGE_TAG to a unique release tag}"
# Reads the region/account and requires a selected image tag.
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
PREFIX="${ECR_PREFIX:-anthony-assessment4}"
# Check existing repositories; never create infrastructure as a build side effect.
for service in fraud forecasting recommendations; do
  # Checks the project repositories exist; it does not create them.
  aws ecr describe-repositories --region "$AWS_REGION" --repository-names "${PREFIX}-${service}" >/dev/null
done
# Authenticates Docker to ECR without printing a password.
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
for service in fraud forecasting recommendations gateway frontend; do
  repo="${PREFIX}-${service}"
  tag="$IMAGE_TAG"
  dockerfile="apps/services/${service}/Dockerfile"
  if [[ "$service" == gateway || "$service" == frontend ]]; then
    repo="${PREFIX}-fraud"
    tag="${service}-${IMAGE_TAG}"
    dockerfile="apps/gateway/Dockerfile"
    [[ "$service" != frontend ]] || dockerfile="dashboard/frontend/Dockerfile"
  fi
  # Builds Linux AMD64 images and uploads them. The hosting image disables OCI attestations for
  # SageMaker compatibility.
  docker buildx build --platform linux/amd64 --push -t "${REGISTRY}/${repo}:${tag}" -f "$dockerfile" .
done
