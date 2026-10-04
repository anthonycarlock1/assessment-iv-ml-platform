import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse

logger = logging.getLogger('assessment.gateway')

app = FastAPI(title='Assessment IV API Gateway')

SERVICE_URLS = {
    'fraud': os.getenv('FRAUD_SERVICE_URL', 'http://fraud-service.fraud-team.svc.cluster.local'),
    'forecasting': os.getenv('FORECASTING_SERVICE_URL', 'http://forecasting-service.fraud-team.svc.cluster.local'),
    'recommendations': os.getenv('RECOMMENDATIONS_SERVICE_URL', 'http://recommendations-service.fraud-team.svc.cluster.local'),
}


async def _proxy_request(service_name: str, payload: Any):
    url = f'{SERVICE_URLS[service_name]}/predict'
    logger.info('gateway.proxy', extra={'service': service_name, 'url': url})

    try:
        response = httpx.post(url, json=payload, timeout=15.0)
        response.raise_for_status()
        return JSONResponse(status_code=response.status_code, content=response.json())
    except httpx.HTTPError as exc:
        logger.exception('gateway.downstream_error', extra={'service': service_name})
        return JSONResponse(status_code=502, content={'detail': f'{service_name} downstream service unavailable', 'error': str(exc)})


@app.get('/health')
def health():
    return {'status': 'healthy', 'service': 'gateway'}


@app.post('/fraud/predict')
async def fraud_predict(payload: dict):
    return await _proxy_request('fraud', payload)


@app.post('/forecasting/predict')
async def forecasting_predict(payload: dict):
    return await _proxy_request('forecasting', payload)


@app.post('/recommendations/predict')
async def recommendations_predict(payload: dict):
    return await _proxy_request('recommendations', payload)
