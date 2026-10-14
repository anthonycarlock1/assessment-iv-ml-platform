# CloudWatch operations

The project uses the Amazon CloudWatch Observability EKS add-on to collect application,
node/dataplane logs, and Container Insights metrics. All five EKS control-plane log
types (API, audit, authenticator, controller manager, scheduler) are enabled.
SageMaker continues to publish its three hosting log groups separately.

The collector has a dedicated Pod Identity role in `amazon-cloudwatch`. Application
Signals and automatic application instrumentation/restarts are disabled. No application
image changes or static AWS credentials are required. Collection runs beside the APIs;
a collector outage does not stop predictions. Logging/metrics/alarms/dashboard usage
incur AWS charges; the five EKS log groups retain data for 14 days.

## Dashboard and alarms

[Open the project dashboard](https://us-east-1.console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/anthony-assessment4-operations)

Dashboard `anthony-assessment4-operations` displays node CPU/memory, container counts
and restarts, SageMaker invocations/server errors/latency, API/history write errors,
DynamoDB throttling, and a recent application Logs Insights table.

| Alarms | Threshold |
| --- | --- |
| Three SageMaker server-error alarms | Any Invocation5XXErrors in one minute |
| Three SageMaker latency alarms | Average ModelLatency above 5,000,000 microseconds (5 seconds) for two minutes |
| API 5xx log events | Any application status >=500 event in one minute |
| DynamoDB history write errors | Any prediction_history_write_failed log event in one minute |
| DynamoDB read/write throttling | Any corresponding throttle event in one minute |
| Node CPU/memory | Cluster average above 80% for three minutes |

All 12 alarms send alarm/recovery actions to SNS topic
`anthony-assessment4-cloudwatch-alarms`. An email subscription is configured for
`anthonycarlock1@gmail.com`. AWS sends a confirmation email; the recipient must click
**Confirm subscription** before alarm/recovery email delivery begins. Missing
metric data is treated as not breaching, accommodating idle serverless endpoints.
These alarms do not replace external uptime checks. API error metrics count log events;
the gateway and downstream API may both log a single failing request.

## Logs

- `/aws/containerinsights/anthony-assessment4-eks/application`: frontend nginx,
  gateway, APIs, and collector logs. Structured API events include service, request ID,
  status, and timing under `log_processed`.
- `/aws/containerinsights/anthony-assessment4-eks/performance`: Container Insights
  embedded metrics.
- `/aws/containerinsights/anthony-assessment4-eks/host` and `/dataplane`: host and
  Kubernetes networking/runtime logs.
- `/aws/eks/anthony-assessment4-eks/cluster`: EKS control-plane logs.
- `/aws/sagemaker/Endpoints/anthony-assessment4-{service}-sagemaker`: hosting logs.

In Logs Insights, select the application group and search a request ID:

```text
fields @timestamp, kubernetes.namespace_name, log_processed.service,
       log_processed.request_id, log_processed.status, log
| filter log_processed.request_id = "YOUR_REQUEST_ID"
| sort @timestamp asc
```

## Provision and verify

Separate `terraform/cloudwatch` state manages collectors, retention, dashboard,
alarms, filters, and SNS. The root foundation also specifies enabled control-plane
log types for future rebuilds. Do not apply root Terraform defaults to configure
observability on an existing cluster: first inspect the saved rebuild variables.

```bash
terraform -chdir=terraform/cloudwatch init
terraform -chdir=terraform/cloudwatch plan -out=cloudwatch.tfplan
terraform -chdir=terraform/cloudwatch apply cloudwatch.tfplan
```

To enable logging in place when the root foundation was created previously:

```bash
aws eks update-cluster-config --region us-east-1 --name anthony-assessment4-eks \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

Wait for the logging update to succeed and the add-on to be ACTIVE, then run:

```bash
.venv/bin/python scripts/verify_cloudwatch.py
.venv/bin/python scripts/verify_prediction_history.py
kubectl -n amazon-cloudwatch get pods,daemonsets,deployments
```

The verifier checks real tagged requests arrive in CloudWatch from the gateway and
all three APIs, frontend access logs, 14-day application retention, the dashboard,
12 alarm actions, all enabled control-plane types, and positive/negative metric-filter
examples. It does not create faults or send alarm notifications.

## Rebuild and rollback

Keep both Terraform state directories. Before destroying EKS, remove the CloudWatch
add-on through a reviewed `terraform/cloudwatch` destroy plan. Log groups use
`skip_destroy=true`, preserving evidence; they require import into the new state
before reapplying after a destroy. An alternative is to retain the observability
state and refresh/reapply after the foundation rebuild, which recreates missing
cluster-bound resources. The Pod Identity agent must exist before creating the
CloudWatch add-on. Recheck the pinned add-on version against the rebuilt EKS version.

Removing the add-on stops collection without changing inference. Disabling control-plane
logging requires an explicit EKS logging update and corresponding foundation edit;
removing the collector alone does not disable it. Retained log groups continue their
retention policy. Dashboard/alarms/SNS can be removed independently through Terraform.

Sources: [AWS add-on installation and configuration](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/install-CloudWatch-Observability-EKS-addon.html),
[AWS collector chart](https://github.com/aws-observability/helm-charts).

## Recorded live verification

The add-on reached ACTIVE with healthy collectors, all five control-plane log types enabled and log events received. Tagged health requests from the gateway and all three APIs arrived in CloudWatch; frontend access logs were also received. Actual CPU, memory, container-count, and restart metric samples were verified. All 12 alarms have SNS actions, the dashboard exists, and metric-filter positive/negative checks passed. All three real SageMaker predictions still persisted to DynamoDB after installation. See [CloudWatch evidence](cloudwatch-verification.json) and [prediction evidence](cloudwatch-prediction-verification.json).
