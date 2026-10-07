# Kubernetes deployment and verification

The live platform uses four workload namespaces:

| Namespace | Workloads | AWS access |
| --- | --- | --- |
| fraud-team | fraud-service | fraud-sagemaker Pod Identity |
| forecasting-team | forecasting-service | forecasting-sagemaker Pod Identity |
| recommendations-team | recommendations-service | recommendations-sagemaker Pod Identity |
| platform-team | frontend-service, gateway-service | No inference IAM role |

Each namespace has a ResourceQuota and a container LimitRange. Budgets accommodate rolling updates and the existing fraud HPA's maximum of three replicas. Quotas are ceilings; they do not reserve or add node capacity. Each deployment specifies CPU/memory requests and limits. ConfigMaps contain endpoint names, region, service URLs and team names. AWS credentials come from Pod Identity rather than committed Secrets.

Startup probes allow 150 seconds for initialization. Liveness probes call `/health`, which checks the running process without invoking SageMaker. Readiness probes call `/ready`: adapters validate required configuration; the gateway checks downstream readiness; nginx checks that its frontend page exists. Adapter readiness is configuration readiness, not a guarantee that the next AWS invocation will succeed. The frontend does not restart when SageMaker is unavailable.

Rebuild and deploy a unique release:

```bash
.venv/bin/python scripts/deploy_sagemaker.py identity
IMAGE_TAG=your-unique-release bash scripts/build.sh
IMAGE_TAG=your-unique-release bash scripts/deploy.sh
.venv/bin/python scripts/verify_kubernetes.py > docs/kubernetes-verification.json
.venv/bin/python scripts/verify_live.py > docs/live-integration-verification.json
.venv/bin/python scripts/verify_live_validation.py > docs/live-validation-verification.json
```

The identity command configures IAM/Pod Identity only; it does not create or update SageMaker endpoints. Forecasting and recommendations use new `-invoke-v2` roles scoped to their own namespaces and endpoints. The original invocation roles and associations remain available for rollback. The trust documents in `aws-iam/` describe the active roles listed in `sagemaker-resource-plan.json`. Existing AWS compute and repositories are preserved.

The deployment script runs pytest, renders all manifests, performs client validation, validates namespace creation on the server, creates any namespace prerequisites, and performs server dry runs before workload application. It installs budgets before the final admission check and waits for each rollout. The verification script checks replicas, pods, selectors, ready EndpointSlices and probe paths. It also uses server dry runs to prove default resource injection, rejection of an oversized container, and rejection of a pod exceeding namespace quota. Those test pods are never created.

The initial single-namespace copies are removed after the new frontend successfully returns real SageMaker predictions. Rollback manifests for the retired Kubernetes copies are saved in `kubernetes-migration-rollback.yaml`. The deploy script does not repeat migration cleanup on subsequent releases.

To open the deployed frontend locally:

```bash
kubectl -n platform-team port-forward --address 127.0.0.1 svc/frontend-service 8080:80
```

Visit `http://localhost:8080`. This tunnels to the EKS frontend. The browser uses `/api/`, and nginx forwards to the gateway in `platform-team`, which routes to the adapter's own namespace. Public exposure is optional: the current cluster has no nginx ingress controller, so the ingress manifests alone do not publish a URL. `k8s/exposure/frontend-public.yaml` can create a billable AWS load balancer when explicitly applied.

The frontend readiness failure/recovery test runs in a disposable Docker container with `bash scripts/verify_frontend_probes.sh <frontend-image>` and is included in CI. Its live local-container evidence is in `frontend-probe-verification.json`.

Runtime failures are additionally logged with service/team, exception type and AWS error code; raw AWS messages and stack traces are not logged by this adapter or returned to users. All newly created resources plus retained rollback identities have `Owner=anthony` tags (`aws-resource-ownership.json`).

Live investigation identified SageMaker `ModelError` with `OriginalStatusCode=0` (no endpoint response). The adapter retries this error and `ModelNotReadyException` once, after 250 ms, only if the first attempt fails within one second. It does not retry malformed input, permission errors, or slow failures. Tests cover successful retry output, the retry limit, and the gateway time budget. Runtime unavailability can still return a sanitized 502 after the bounded retry.

Final deployed release: `namespace-integration-20261005-v3`. Verification passed: 99 pytest tests, both manifest dry runs, seven ready pods with zero restarts, namespace admission checks, nine repeated real SageMaker predictions, and seven safe invalid-input responses. The live evidence files reflect this release.
