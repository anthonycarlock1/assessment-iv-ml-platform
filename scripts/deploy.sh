#!/usr/bin/env bash
# Stops if a required command fails.
set -euo pipefail
cd "$(dirname "$0")/.."
# Selects release tag, AWS account/region, existing cluster, and Python executable.
export IMAGE_TAG="${IMAGE_TAG:?Set IMAGE_TAG to the tag built by build.sh}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
EKS_CLUSTER_NAME="${EKS_CLUSTER_NAME:-anthony-assessment4-eks}"
PYTHON="${PYTHON:-.venv/bin/python}"
# Tests must pass before changing workloads.
# Requires Python tests to pass before workload changes.
"$PYTHON" -m pytest -q apps tests
# Renders release manifests and cleans up its own temporary file on exit.
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
"$PYTHON" scripts/render_manifests.py > "$manifest"
# Points kubectl at the existing cluster.
aws eks update-kubeconfig --region "$AWS_REGION" --name "$EKS_CLUSTER_NAME"
# Checks the manifests locally.
kubectl apply --dry-run=client -f "$manifest" >/dev/null
# Namespaces must exist before admission can validate namespaced resources.
# Validates on the live API server, creates namespace prerequisites, applies budgets, then checks
# admission again.
kubectl apply --dry-run=server -f k8s/namespaces >/dev/null
kubectl apply -f k8s/namespaces
kubectl apply --dry-run=server -f "$manifest" >/dev/null
# Enforce namespace budgets before creating or updating workloads.
kubectl apply -f k8s/policies
kubectl apply --dry-run=server -f "$manifest" >/dev/null
# Applies the validated resources; this does not rebuild EKS or ECR.
kubectl apply -f "$manifest"
# Waits for each Deployment in its correct namespace before declaring the release complete.
for service in fraud forecasting recommendations gateway frontend; do
  case "$service" in
    fraud|forecasting|recommendations) namespace="${service}-team" ;;
    gateway|frontend) namespace=platform-team ;;
  esac
  kubectl -n "$namespace" rollout status "deployment/${service}-service" --timeout=180s
done
kubectl -n platform-team get ingress
