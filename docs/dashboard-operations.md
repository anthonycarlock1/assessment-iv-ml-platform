# Operations dashboard

The UI displays owning team, separate health and readiness, model/version, deployed service version, inference provider, and SageMaker endpoint/region. Operational metadata comes from each adapter's typed `/metadata` API through `/api/{service}/metadata`; it does not require a prediction or invoke AWS. Missing metadata is shown as unavailable.

Health, readiness, and metadata each poll independently every 15 seconds after the previous response, with a five-second timeout. Each result updates immediately. Checks do not overlap, and navigating away aborts pending checks and clears timers. A failed or slow service does not block other services or their prediction forms. Loading, errors, last-check times, and temporary updates are visible.

The dashboard implements three of the optional requirements: live polling, version display, and a compact test-request interface. Sample input fields are examples submitted to real APIs, not static prediction results or operational state. No request-count metric is claimed.

Adapter configuration uses `TEAM_NAME`, `MODEL_NAME`, `MODEL_VERSION`, and `SERVICE_VERSION`; SageMaker endpoint names and region remain in the existing ConfigMaps. The manifest renderer sets `SERVICE_VERSION` to the release image tag. Gateway route tests include metadata and assert that each route calls exactly its own downstream service.

Validation:

```bash
.venv/bin/python -m pytest -q apps tests
cd dashboard/frontend
npm test
npm run build
npm run lint
```

Polling tests cover an indefinitely slow service alongside healthy and failed services, automatic recovery, non-overlapping manual refresh, and cancellation after unmount. API tests assert configured metadata, typed responses, missing-configuration behavior, and that metadata never invokes SageMaker. The CI validation job runs the frontend polling tests.

Live verification helpers:

```bash
.venv/bin/python scripts/verify_dashboard_api.py > docs/dashboard-api-verification.json
```

`verify_dashboard_browser.cjs` additionally checks the rendered page, automatic polling, a browser-only simulated forecasting outage, a real SageMaker fraud prediction while that outage is visible, and recovery. It requires Playwright tooling plus a browser; it does not modify AWS services. An example using temporary tooling and an installed Chrome is:

```bash
npm install --prefix /tmp/anthony-dashboard-browser --no-save --package-lock=false playwright
NODE_PATH=/tmp/anthony-dashboard-browser/node_modules \
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
node scripts/verify_dashboard_browser.cjs
```

The deployed frontend is accessible with `kubectl -n platform-team port-forward --address 127.0.0.1 svc/frontend-service 8080:80`, then `http://localhost:8080`.

Verified deployed release: `dashboard-ops-20261006-v1`. All 106 Python tests and three polling tests passed; frontend build/lint and Kubernetes client/server dry runs passed. Seven pods were ready with zero restarts. The real-browser test confirmed API-backed metadata, recurring polls for all nine checks, isolated simulated failure, a real SageMaker fraud prediction during that failure, and recovery. Evidence: `dashboard-api-verification.json`, `dashboard-browser-verification.json`, and `dashboard-operations.png`.

All three services also passed final semantic SageMaker prediction checks through the deployed frontend proxy (`live-integration-verification.json`). No SageMaker endpoint, cluster, node group, or ECR repository was recreated.
