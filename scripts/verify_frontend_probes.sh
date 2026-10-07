#!/usr/bin/env bash
# Exercise nginx probe behavior in a disposable container, without touching EKS.
set -euo pipefail
# Requires the frontend image to inspect.
image="${1:?Pass the frontend image to test}"
container="anthony-frontend-probes-$$"
# Deletes only the temporary test container when the script exits.
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
# Starts nginx with a harmless local gateway-DNS mapping.
docker run --detach --name "$container" --add-host gateway-service.platform-team.svc.cluster.local:127.0.0.1 "$image" >/dev/null
# Wait for nginx startup without restarting it.
# Waits for nginx health before testing readiness.
for attempt in {1..30}; do
  if docker exec "$container" wget -q -O /dev/null http://127.0.0.1/health; then break; fi
  sleep 1
done
# Checks normal health/readiness, temporarily moves the index page, proves health stays 200 while
# readiness is 503, then restores the page.
docker exec "$container" sh -ec '
  wget -q -O /dev/null http://127.0.0.1/health
  wget -q -O /dev/null http://127.0.0.1/ready
  mv /usr/share/nginx/html/index.html /tmp/index.html
  wget -q -O /dev/null http://127.0.0.1/health
  if wget -S -O /dev/null http://127.0.0.1/ready 2>/tmp/ready-error; then exit 1; fi
  grep -q "503" /tmp/ready-error
  mv /tmp/index.html /usr/share/nginx/html/index.html
  wget -q -O /dev/null http://127.0.0.1/ready
'
# Prints JSON recording the probe assertions.
printf '%s\n' '{"healthy_frontend_ready":true,"missing_page_ready_status":503,"missing_page_health_status":200,"restored_page_ready":true}'
