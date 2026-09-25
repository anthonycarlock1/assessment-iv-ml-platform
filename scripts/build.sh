#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: build.sh [--tag TAG] [--region REGION]

Builds and pushes all ML service containers to ECR.

Examples:
  ./scripts/build.sh
  ./scripts/build.sh --tag v1
  AWS_REGION=us-east-1 ./scripts/build.sh --tag latest
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
AWS_REGION="${AWS_REGION:-us-east-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)
      IMAGE_TAG="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is required but not installed." >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but not installed." >&2
  exit 1
fi

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text --region "$AWS_REGION" 2>/dev/null || true)}"
if [[ -z "$AWS_ACCOUNT_ID" ]]; then
  echo "Unable to determine AWS account ID. Ensure you are authenticated with AWS CLI." >&2
  exit 1
fi

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

declare -A REPOS=(
  [fraud]="anthony-assessment4-fraud"
  [forecasting]="anthony-assessment4-forecasting"
  [recommendations]="anthony-assessment4-recommendations"
)

for SERVICE in fraud forecasting recommendations; do
  REPO_NAME="${REPOS[$SERVICE]}"
  echo "Ensuring repository exists: ${REPO_NAME}"
  aws ecr describe-repositories --region "$AWS_REGION" --repository-names "$REPO_NAME" >/dev/null 2>&1 || \
    aws ecr create-repository --region "$AWS_REGION" --repository-name "$REPO_NAME" --image-scanning-configuration scanOnPush=true --encryption-configuration encryptionType=AES256 >/dev/null

  LOCAL_TAG="${REPO_NAME}:${IMAGE_TAG}"
  REMOTE_TAG="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}"

  echo "Building ${SERVICE} image: ${LOCAL_TAG}"
  docker build -t "$LOCAL_TAG" -f "apps/services/${SERVICE}/Dockerfile" "apps/services/${SERVICE}"

  echo "Tagging ${LOCAL_TAG} -> ${REMOTE_TAG}"
  docker tag "$LOCAL_TAG" "$REMOTE_TAG"

  echo "Pushing ${REMOTE_TAG}"
  docker push "$REMOTE_TAG"

done

echo "Build and push completed successfully."
