#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-us-east-1}"
OWNER="${OWNER:-anthony}"

# Targets the three owner-prefixed repositories.
repos=(
  "${OWNER}-assessment4-forecasting"
  "${OWNER}-assessment4-fraud"
  "${OWNER}-assessment4-recommendations"
)

for repo in "${repos[@]}"; do
  echo "Checking repository: $repo"
  # Lists all image IDs and skips an empty repository.
  image_ids=$(aws ecr list-images \
    --region "$AWS_REGION" \
    --repository-name "$repo" \
    --query 'imageIds[*]' \
    --output json)

  if [[ "$image_ids" == "[]" || "$image_ids" == "" ]]; then
    echo "Repository $repo is already empty."
    continue
  fi

  echo "Deleting images in $repo..."
  # Deletes the listed images, including potentially deployed releases; stops on deletion failure.
  aws ecr batch-delete-image \
    --region "$AWS_REGION" \
    --repository-name "$repo" \
    --image-ids "$(printf '%s' "$image_ids")" || {
      echo "Failed to delete images for $repo"
      exit 1
    }

done

echo "ECR cleanup complete."
