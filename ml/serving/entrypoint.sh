#!/bin/sh
set -eu
# Accepts SageMaker’s serve startup argument and rejects other commands.
if [ "${1:-serve}" != serve ]; then
  echo "Expected SageMaker serve argument" >&2
  exit 1
fi
# Starts the hosting FastAPI app on port 8080 with one worker, replacing the shell process.
exec uvicorn ml.serving.main:app --host 0.0.0.0 --port 8080 --workers 1
