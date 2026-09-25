#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bootstrap.sh [--region REGION] [--validate-only]

Validates AWS access, refreshes kubeconfig, and applies the Kubernetes manifests needed for the platform.

Examples:
  ./scripts/bootstrap.sh
  ./scripts/bootstrap.sh --region us-east-1
  ./scripts/bootstrap.sh --validate-only
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

AWS_REGION="${AWS_REGION:-us-east-1}"
VALIDATE_ONLY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --validate-only)
      VALIDATE_ONLY="true"
      shift
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

aws sts get-caller-identity --region "$AWS_REGION" >/dev/null
aws eks update-kubeconfig --region "$AWS_REGION" --name anthony-assessment4-eks >/dev/null
kubectl get nodes >/dev/null

if [[ "$VALIDATE_ONLY" == "true" ]]; then
  echo "AWS access and Kubernetes connectivity validated."
  exit 0
fi

kubectl apply -f k8s/namespaces/fraud-team.yaml
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/ingress/ingress.yaml

echo "Bootstrap complete. Kubernetes manifests applied."
