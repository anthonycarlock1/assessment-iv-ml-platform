# Brings in the libraries, shared code, and test or runtime settings needed below.
import asyncio
import os
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from apps.services.common.observability import instrument
from apps.services.common.validation import install_validation_handler, require_finite_json

# Reads each downstream URL from configuration, with cross-namespace Service DNS defaults.
SERVICE_URLS = {name: os.getenv(f'{name.upper()}_SERVICE_URL', f'http://{name}-service.{name}-team.svc.cluster.local')
                for name in ('fraud', 'forecasting', 'recommendations')}
TIMEOUT = httpx.Timeout(75, connect=3)
app = FastAPI(title='Assessment IV API Gateway')
instrument(app, 'gateway')
install_validation_handler(app)

# Sends one HTTP request to a downstream API using an explicit timeout.
async def downstream(method, url, **kwargs):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await client.request(method, url, **kwargs)

# Builds the selected service URL, forwards the request ID, and converts downstream/network
# failures into safe gateway responses.
async def proxy(service, path, request, payload=None):
    url = SERVICE_URLS[service].rstrip('/') + '/' + path
    try:
        response = await downstream('POST' if payload is not None else 'GET', url,
            **({'json': payload} if payload is not None else {}),
            headers={'x-request-id': request.state.request_id})
        if response.status_code >= 500:
            return JSONResponse(status_code=502, content={'detail': 'Downstream service unavailable'})
        if response.status_code >= 400 and response.status_code != 422:
            return JSONResponse(status_code=response.status_code, content={'detail': 'Downstream request rejected'})
        return JSONResponse(status_code=response.status_code, content=response.json())
    except (httpx.HTTPError, ValueError):
        return JSONResponse(status_code=502, content={'detail': 'Downstream service unavailable'})

@app.get('/health')
# Reports gateway process liveness without depending on the downstream APIs.
def health():
    return {'status': 'healthy', 'service': 'gateway'}

@app.get('/ready')
# Checks service URL configuration and all downstream readiness responses; reports 503 when any
# required service is unavailable.
async def ready(request: Request):
    if any(not url.startswith(('http://', 'https://')) for url in SERVICE_URLS.values()):
        return JSONResponse(status_code=503, content={'detail': 'Service URL configuration missing'})
    results = await asyncio.gather(*(proxy(service, 'ready', request) for service in SERVICE_URLS))
    for service, result in zip(SERVICE_URLS, results):
        if result.status_code != 200:
            return JSONResponse(status_code=503, content={'detail': f'{service} unavailable'})
    return {'status': 'ready', 'service': 'gateway'}

# Creates prediction, health, readiness, and metadata routes for one specific service.
def register(service):
    # Rejects non-finite JSON and forwards this service’s prediction request.
    async def predict(request: Request, payload: dict):
        require_finite_json(payload)
        return await proxy(service, 'predict', request, payload)
    # Forwards only this service’s health check.
    async def health(request: Request):
        return await proxy(service, 'health', request)
    # Forwards only this service’s readiness check.
    async def ready(request: Request):
        return await proxy(service, 'ready', request)
    # Forwards only this service’s metadata request.
    async def metadata(request: Request):
        return await proxy(service, 'metadata', request)
    app.get(f'/{service}/metadata')(metadata)
    app.post(f'/{service}/predict')(predict)
    app.get(f'/{service}/health')(health)
    app.get(f'/{service}/ready')(ready)

# Installs the four routes for fraud, forecasting, and recommendations.
for service in SERVICE_URLS:
    register(service)
