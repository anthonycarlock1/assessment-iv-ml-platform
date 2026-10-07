# Implemented architecture

The browser loads the deployed React static frontend through an optional public LoadBalancer Service or existing nginx ingress. With the public Service, the frontend nginx server proxies `/api/` to the gateway. Same-origin `/api` requests are rewritten to gateway routes such as `/fraud/predict`. The gateway forwards a request to exactly one ClusterIP service, preserving the request ID and validation failures. The FastAPI service validates the request, delegates feature transformation and inference to its engine, and validates the response.

Deployed inference invokes three SageMaker serverless endpoints that load the existing joblib artifacts. EKS pods use dedicated Pod Identity roles scoped to their respective endpoint. Local inference remains available for development. Forecasting uses newest-first lag features. Recommendations use catalog-wide training-compatible category/item codes and click probabilities. The optional SageMaker adapter accepts an injected client, sets AWS timeouts, and wraps downstream errors without implicit fallback.

No application database or API key is required. AWS credentials are used by deployment tooling; SageMaker mode additionally requires workload IAM. Existing Terraform resources remain unchanged. Read-only inspection found no ingress controller. The optional `k8s/exposure/frontend-public.yaml` creates a public load balancer only when explicitly applied; default deployment does not apply it.

Readiness verifies model/configuration availability. It is separate from process liveness. JSON logs include team, service, request ID, HTTP status, and duration. Frontend duration measures the browser round trip and is not advertised as platform-wide telemetry.

## Workload namespaces

Fraud runs in `fraud-team`, forecasting in `forecasting-team`, recommendations in `recommendations-team`, and the frontend/gateway in `platform-team`. Each namespace has resource budgets and container defaults. The gateway uses cross-namespace Service DNS names, and each adapter uses a namespace-scoped EKS Pod Identity role for its own SageMaker endpoint. See [Kubernetes verification](../kubernetes-deployment.md).
