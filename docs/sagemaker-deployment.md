# SageMaker inference deployment

The three models are hosted as separate on-demand serverless endpoints in us-east-1:

- anthony-assessment4-fraud-sagemaker
- anthony-assessment4-forecasting-sagemaker
- anthony-assessment4-recommendations-sagemaker

Each endpoint uses 2048 MB and maximum concurrency 2, with no provisioned concurrency. Existing model artifacts and their inference transformations are baked into a single Docker image stored with a distinct tag/digest in the existing fraud ECR repository. `SERVICE_NAME` selects the correct model inside each hosting container. This requires no SageMaker training job, notebook, Studio domain, or new S3 bucket. CloudWatch receives hosting logs.

The container listens on 8080 and implements `/ping` and `/invocations`. Its entrypoint accepts SageMaker's `serve` argument. A single worker loads one model copy. EKS continues to run the HTTP APIs; `MODEL_PROVIDER=sagemaker` selects invocation of the hosted endpoint rather than in-pod inference. Runtime errors never switch providers.

AWS identity uses four dedicated project roles: one hosting execution role with scoped ECR/log access and three service roles with permission to invoke only their respective endpoints. EKS Pod Identity associates those service roles with the three Kubernetes service accounts. The agent add-on is required on the existing cluster; no OIDC-provider changes are needed. The node role must have `eks-auth:AssumeRoleForPodIdentity` (included in the current AmazonEKSWorkerNodePolicy). No static keys are mounted in pods.

## Repeatable commands

Use the project `.venv` and authenticated AWS CLI. Preview is offline:

```bash
.venv/bin/python scripts/deploy_sagemaker.py plan
export IMAGE_TAG=sm-20261004-v1
bash scripts/build_sagemaker.sh
```

The build prints the ECR image digest. Set `IMAGE_URI` to the full immutable image URI, then:

```bash
.venv/bin/python scripts/deploy_sagemaker.py provision --image "$IMAGE_URI" --release sm-v1
.venv/bin/python scripts/deploy_sagemaker.py status
```

Provision creates only project-specific IAM roles/policies, Pod Identity agent/associations, and SageMaker models/configurations/endpoints. It refuses unexpected existing roles or endpoint release collisions. No deletes, endpoint replacements, Terraform apply/destroy, cluster/node group changes, or repository creation are performed.

After all endpoints are InService:

```bash
.venv/bin/python scripts/deploy_sagemaker.py verify
.venv/bin/python scripts/deploy_sagemaker.py bind
export IMAGE_TAG=sagemaker-integration-v1
bash scripts/build.sh
bash scripts/deploy.sh
```

`verify` actually invokes each AWS endpoint and validates semantic results. `bind` repeats that check before changing any application manifests. It switches ConfigMaps to SageMaker and assigns the correct service accounts; normal rendering/deployment includes those accounts. An InService status alone is not considered a verified prediction.

Readiness checks configuration, not a live SageMaker call. The first prediction may incur a serverless cold start. Timeouts allow 70 seconds at the AWS client, 75 seconds at the gateway, 85 seconds at nginx, and 90 seconds in the browser. A cold-start capacity error can still require retrying the request; no automatic local fallback occurs.

Your cluster originally had no public load balancer or ingress controller. The separately optional `k8s/exposure/frontend-public.yaml` exposes the hosted frontend if explicitly applied. That creates a billable load balancer; it is not applied by the SageMaker provisioning script.

## Account permissions

The deployer needs SageMaker create/describe/list model, endpoint config, endpoint and InvokeEndpoint; ECR push/read; IAM create/get/tag roles, PutRolePolicy and PassRole; EKS list/create/describe add-ons and list/create/describe Pod Identity associations; and Kubernetes workload-management access in fraud-team, forecasting-team, recommendations-team, and platform-team. Permissions can be restricted to the project resource names wherever supported.

If AWS rejects an operation, an account administrator/instructor must grant it or perform the project-specific identity setup. Never reuse another student's role/endpoints or broaden the worker-node role with SageMaker access to bypass missing deployment permissions.

## Costs

On-demand serverless endpoints scale to zero between requests. AWS's 2 GB pricing example uses $0.00004 per billed compute second; 3,000 invocations billed at one second each would be approximately $0.12 in compute, plus data processing, ECR storage, CloudWatch, and existing infrastructure charges. This is an example, not a cap or billing guarantee. No provisioned concurrency is requested.

Sources: [SageMaker pricing](https://aws.amazon.com/sagemaker/ai/pricing/), [serverless endpoint behavior](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html), [custom hosting contract](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html), [EKS Pod Identity](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-role.html).

Ownership can be verified with `.venv/bin/python scripts/audit_aws_ownership.py`. The inventory in `docs/aws-resource-ownership.json` records the active resources and identities retained for rollback with `Owner=anthony`. Generic-name EKS-managed resources are identified through their owner/project tags; SageMaker and IAM resource names also start with `anthony-assessment4`.

## Verified live deployment

All three endpoints reached InService and semantic predictions passed both direct SageMaker invocation and the deployed frontend -> gateway -> FastAPI path. Application images now use release `dashboard-ops-20261006-v1`. See `docs/live-integration-verification.json`. To access the hosted frontend without adding a public load balancer, run:

```bash
kubectl -n platform-team port-forward --address 127.0.0.1 svc/frontend-service 8080:80
```

Open http://127.0.0.1:8080. Only the connection is tunneled through your laptop; the frontend, gateway, and APIs run in EKS, and models run in SageMaker. No Vite/local inference process is used.

## Validation and error handling

API request validation returns serializable 422 errors with field locations, messages, and error types; raw input/context are omitted. Gateway routes reject nested non-finite JSON numbers before forwarding. SageMaker ModelError responses whose OriginalStatusCode indicates invalid input (400, 413, 415, or 422) become sanitized API 422 responses. Authentication/permission failures and model server failures remain 502. Readiness tests independently cover missing region and endpoint configuration for all three services; logging tests assert service, team, request ID, status, and duration.

AWS reference: [InvokeEndpoint ModelError fields](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html).

Application validation fixes were deployed as release `validation-fixes-v1`. All 93 pytest tests passed; seven live invalid-input checks returned 422 and all three valid-prediction checks returned SageMaker results. Evidence: `docs/live-validation-verification.json` and `docs/live-integration-verification.json`. A first valid request returned a temporary 502; retry succeeded. Serverless cold-start availability remains separate from request validation.

The Kubernetes namespace/probe/budget gaps were addressed in release `namespace-integration-20261005-v1`. See [deployment details](kubernetes-deployment.md) and `kubernetes-verification.json` for live rollout and server-side admission evidence.
