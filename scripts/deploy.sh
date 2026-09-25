#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: deploy.sh [--tag TAG] [--region REGION] [--namespace NAMESPACE]

Applies Kubernetes manifests and updates the running deployments to the selected image tag.

Examples:
  ./scripts/deploy.sh
  ./scripts/deploy.sh --tag v1
  AWS_REGION=us-east-1 ./scripts/deploy.sh --tag latest
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_TAG="${IMAGE_TAG:-latest}"
AWS_REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="${NAMESPACE:-fraud-team}"

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
    --namespace)
      NAMESPACE="$2"
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

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required but not installed." >&2
  exit 1
fi

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text --region "$AWS_REGION" 2>/dev/null || true)}"
if [[ -z "$AWS_ACCOUNT_ID" ]]; then
  echo "Unable to determine AWS account ID. Ensure you are authenticated with AWS CLI." >&2
  exit 1
fi

EKS_CLUSTER_NAME="${EKS_CLUSTER_NAME:-${OWNER:-anthony}-${PROJECT_NAME:-anthony-assessment4}-eks}"
aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER_NAME" >/dev/null

kubectl apply -f k8s/namespaces/fraud-team.yaml
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/ingress/ingress.yaml

declare -A IMAGE_REPOS=(
  [fraud]="${OWNER:-anthony}-${PROJECT_NAME:-anthony-assessment4}-fraud"
  [forecasting]="${OWNER:-anthony}-${PROJECT_NAME:-anthony-assessment4}-forecasting"
  [recommendations]="${OWNER:-anthony}-${PROJECT_NAME:-anthony-assessment4}-recommendations"
)

declare -A DEPLOYMENTS=(
  [fraud]="fraud-service"
  [forecasting]="forecasting-service"
  [recommendations]="recommendations-service"
)

declare -A CONTAINERS=(
  [fraud]="fraud-service"
  [forecasting]="forecasting"
  [recommendations]="recommendations-service"
)

for SERVICE in fraud forecasting recommendations; do
  REPO_NAME="${IMAGE_REPOS[$SERVICE]}"
  DEPLOYMENT_NAME="${DEPLOYMENTS[$SERVICE]}"
  CONTAINER_NAME="${CONTAINERS[$SERVICE]}"
  IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}:${IMAGE_TAG}"

  echo "Updating ${DEPLOYMENT_NAME} with image ${IMAGE_URI}"
  kubectl -n "$NAMESPACE" set image deployment/${DEPLOYMENT_NAME} ${CONTAINER_NAME}="${IMAGE_URI}"
  kubectl -n "$NAMESPACE" rollout status deployment/${DEPLOYMENT_NAME} --timeout=180s

done

echo "Deployment completed successfully."
