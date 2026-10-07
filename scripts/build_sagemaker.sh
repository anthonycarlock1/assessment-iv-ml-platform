#!/usr/bin/env bash
# Stops on command errors, missing variables, or failed pipelines.
set -euo pipefail
cd "$(dirname "$0")/.."
# Reads the region/account and requires a selected image tag.
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
IMAGE_TAG="${IMAGE_TAG:?Set IMAGE_TAG to a unique release}"
REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REPOSITORY="anthony-assessment4-fraud"
# Checks the project repositories exist; it does not create them.
aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$REPOSITORY" >/dev/null
# Authenticates Docker to ECR without printing a password.
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$REGISTRY"
# SageMaker requires a single-platform Docker V2 image; omit OCI attestations.
# Builds Linux AMD64 images and uploads them. The hosting image disables OCI attestations for
# SageMaker compatibility.
docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
  --output type=image,push=true,oci-mediatypes=false \
  -t "${REGISTRY}/${REPOSITORY}:sagemaker-${IMAGE_TAG}" -f ml/serving/Dockerfile .
aws ecr describe-images --region "$AWS_REGION" --repository-name "$REPOSITORY" \
  --image-ids "imageTag=sagemaker-${IMAGE_TAG}" --query 'imageDetails[0].imageDigest' --output text
