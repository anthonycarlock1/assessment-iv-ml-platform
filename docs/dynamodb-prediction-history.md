# DynamoDB prediction history

Table: `anthony-assessment4-prediction-history` in `us-east-1`. Partition key
`service` isolates fraud, forecasting, and recommendations. Sort key `event_id`
combines a UTC timestamp with a UUID. Records contain validated prediction inputs,
results, request IDs, and a 30-day `expires_at` TTL. JSON strings preserve floating
point values without DynamoDB Decimal serialization issues.

The table uses on-demand billing, encryption at rest, and point-in-time recovery.
Storage, requests, and recovery incur AWS charges. Owner/project tags identify it.
Each existing Pod Identity role receives a separate policy granting only PutItem
and Query on this table, restricted to its service partition with LeadingKeys.
The SageMaker policy, roles, endpoints, and EKS foundation are preserved.

## Provision and deploy

Run from the repository root with authenticated AWS access. Existing project Pod
Identity roles must already exist. This directory has independent Terraform state;
do not apply the EKS foundation to add this table.

```bash
terraform -chdir=terraform/dynamodb init
terraform -chdir=terraform/dynamodb plan -out=history.tfplan
terraform -chdir=terraform/dynamodb apply history.tfplan
export IMAGE_TAG="history-$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build.sh
bash scripts/deploy.sh
```

Keep the independent Terraform state. Foundation destroy does not remove this
table or its IAM policies. For a full teardown, destroy this storage configuration
before deleting the Pod Identity roles; destroying it removes saved history. It
does not change EKS/SageMaker infrastructure. Before redeploying rebuilt APIs,
apply the storage configuration again after the workload roles have been restored.

## Behavior and API

Successful predictions schedule an in-process background write after the response.
History is best effort, not an audit log: outages/restarts can lose writes. Writes
have one-second connect/two-second read timeouts with SDK retries disabled.
Storage failures produce a sanitized `prediction_history_write_failed` log event
without affecting prediction responses or health/readiness. Invalid/failed
predictions are not saved. History reads use a strongly consistent bounded Query,
return newest-first records, and exclude expired items. No table Scan is used.

Local configuration defaults to disabled. Use `PREDICTION_HISTORY_ENABLED=true`,
`PREDICTION_HISTORY_TABLE`, and `AWS_REGION` to enable it. Kubernetes ConfigMaps
enable it for the three deployed APIs. These are non-sensitive settings;
credentials still come from Pod Identity.

`GET /api/{service}/history?limit=10` returns `{enabled, items}`; limit is 1–50.
Disabled history returns `{enabled: false, items: []}`; unavailable enabled storage
returns an error. History is shared by service, with no user authentication or
per-user privacy boundary, like the existing assessment prediction APIs. Use
assessment sample inputs. The dashboard loads history only on demand and leaves
prediction forms/status polling independent of history availability.

## Verify and rollback

```bash
.venv/bin/python -m pytest -q apps tests
.venv/bin/python scripts/verify_prediction_history.py
```

The live verifier submits a real prediction for every service through the deployed
frontend proxy, then queries history until the matching request ID is present.
These requests create ordinary history records that expire after 30 days.

`scripts/verify_history_browser.cjs` verifies on-demand history in all three forms
and a successful SageMaker prediction during a browser-only simulated history
outage. With the frontend port-forward running, temporary Playwright tooling, and
Chrome installed:

```bash
npm install --prefix /tmp/assessment4-history-browser --no-save --package-lock=false playwright
NODE_PATH=/tmp/assessment4-history-browser/node_modules \
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
node scripts/verify_history_browser.cjs
```

To disable history, set `PREDICTION_HISTORY_ENABLED` to `"false"` in all three
service ConfigMaps and redeploy/restart their Deployments. Pods load environment
variables at startup; editing a ConfigMap alone does not update running pods.
The table can remain intact for later use, and no SageMaker change is required.

## Recorded deployment evidence

Release `history-20261014T002558Z` passed 114 Python tests, frontend build/lint and three polling tests, Terraform validation, and Kubernetes client/server dry runs. All seven application pods were ready with zero restarts. The DynamoDB table was ACTIVE with on-demand billing, encryption, TTL, and point-in-time recovery enabled.

All three services returned real SageMaker predictions and retrieved matching DynamoDB records through the deployed frontend proxy. Browser verification confirmed history display for all three forms, no automatic history polling, and a successful SageMaker prediction during a browser-only simulated history outage. See [API verification](dynamodb-history-verification.json) and [browser verification](dynamodb-history-browser-verification.json). These files record verification results, not ongoing monitoring.
