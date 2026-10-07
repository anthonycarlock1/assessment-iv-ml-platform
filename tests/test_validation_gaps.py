# Brings in the libraries, shared code, and test or runtime settings needed below.
import json
import logging
from unittest.mock import Mock, AsyncMock

import httpx
import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient

from apps.services.common.api import create_app
from apps.services.common.inference import InferenceEngine
from apps.services.common.sagemaker_adapter import SageMakerRuntimeAdapter
from apps.services.common.schemas import Transaction, FraudResponse, ForecastRequest, ForecastResponse, RecommendationRequest, RecommendationResponse
from apps.services.common.observability import logger
from apps.gateway import main as gateway

CONTRACTS = {
    'fraud': (Transaction, FraudResponse, {'amount':1, 'transaction_count':1, 'account_age_days':1}),
    'forecasting': (ForecastRequest, ForecastResponse, {'values':[1,2,3], 'periods':2}),
    'recommendations': (RecommendationRequest, RecommendationResponse, {'user_id':1,'category':'unknown','limit':2}),
}

# Builds a service API around a replaceable runtime for tests.
def make_app(service, adapter=None):
    request_model, response_model, _ = CONTRACTS[service]
    engine = InferenceEngine(service, provider='sagemaker', adapter=adapter)
    return create_app(service, request_model, response_model, engine)

@pytest.mark.parametrize('service', CONTRACTS)
@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity'])
# Checks NaN/Infinity input gets a safe, serializable 422 response.
def test_nonfinite_request_is_safe_422(service, number):
    runtime = Mock()
    adapter = SageMakerRuntimeAdapter(service, 'us-east-1', 'test-endpoint', runtime)
    client = TestClient(make_app(service, adapter), raise_server_exceptions=False)
    payload = CONTRACTS[service][2].copy()
    if service == 'forecasting':
        body = json.dumps({**payload, 'values':[float(number)]})
    else:
        payload['amount' if service == 'fraud' else 'user_id'] = float(number)
        body = json.dumps(payload)
    response = client.post('/predict', content=body, headers={'Content-Type':'application/json'})
    assert response.status_code == 422
    assert response.json()['detail'][0]['loc'][0] == 'body'
    assert all('input' not in error and 'ctx' not in error for error in response.json()['detail'])
    runtime.invoke_endpoint.assert_not_called()

@pytest.mark.parametrize('service', CONTRACTS)
@pytest.mark.parametrize('number', ['NaN', 'Infinity', '-Infinity'])
# Checks nested invalid numbers are rejected before any downstream call.
def test_gateway_rejects_nonfinite_before_downstream(monkeypatch, service, number):
    downstream = AsyncMock()
    monkeypatch.setattr(gateway, 'downstream', downstream)
    response = TestClient(gateway.app).post(f'/{service}/predict', content='{"nested":[{"value":'+number+'}]}', headers={'Content-Type':'application/json'})
    assert response.status_code == 422
    assert response.json()['detail'] == 'JSON numbers must be finite'
    downstream.assert_not_awaited()

@pytest.mark.parametrize('service', CONTRACTS)
@pytest.mark.parametrize('missing', ['endpoint', 'region'])
# Checks missing endpoint and missing region separately for every service.
def test_readiness_requires_each_configuration_value(monkeypatch, service, missing):
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv(f'{service.upper()}_SAGEMAKER_ENDPOINT', 'test-endpoint')
    monkeypatch.delenv('AWS_REGION' if missing == 'region' else f'{service.upper()}_SAGEMAKER_ENDPOINT')
    runtime = Mock()
    adapter = SageMakerRuntimeAdapter(service, client=runtime)
    client = TestClient(make_app(service, adapter))
    assert client.get('/health').json() == {'status':'healthy','service':service}
    assert client.get('/ready').status_code == 503
    assert client.post('/predict',json=CONTRACTS[service][2]).status_code == 503
    runtime.invoke_endpoint.assert_not_called()

@pytest.mark.parametrize('service', CONTRACTS)
@pytest.mark.parametrize('original_status', [400, 413, 415, 422])
# Checks hosted input errors become safe 422 responses through both the service and gateway.
def test_model_input_error_is_422_without_private_details(monkeypatch, service, original_status):
    runtime = Mock()
    runtime.invoke_endpoint.side_effect = ClientError({'Error':{'Code':'ModelError','Message':'private stack trace'},'OriginalStatusCode':original_status},'InvokeEndpoint')
    adapter = SageMakerRuntimeAdapter(service, 'us-east-1', 'test-endpoint', runtime)
    service_app = make_app(service, adapter)
    # Sends one HTTP request to a downstream API using an explicit timeout.
    async def downstream(method, url, **kwargs):
        assert url == gateway.SERVICE_URLS[service] + '/predict'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=service_app),base_url='http://service') as client:
            return await client.request(method,'/predict',**kwargs)
    monkeypatch.setattr(gateway, 'downstream', downstream)
    response = TestClient(gateway.app).post(f'/{service}/predict',json=CONTRACTS[service][2])
    assert response.status_code == 422
    assert response.json() == {'detail':'Inference input rejected; check request values'}
    assert 'private' not in response.text
    runtime.invoke_endpoint.assert_called_once()

@pytest.mark.parametrize('code,status', [('ModelError',500),('ModelError',403),('AccessDenied',422)])
# Checks server/permission failures remain 502 and do not leak private messages.
def test_runtime_or_permission_errors_remain_502(code,status):
    runtime = Mock()
    runtime.invoke_endpoint.side_effect = ClientError({'Error':{'Code':code,'Message':'private'},'OriginalStatusCode':status},'InvokeEndpoint')
    adapter = SageMakerRuntimeAdapter('fraud','us-east-1','test-endpoint',runtime)
    response = TestClient(make_app('fraud',adapter)).post('/predict',json=CONTRACTS['fraud'][2])
    assert response.status_code == 502
    assert 'private' not in response.text

@pytest.mark.parametrize('service', [*CONTRACTS, 'gateway'])
@pytest.mark.parametrize('supplied_id', ['test-request-123', 'bad id with spaces'])
# Checks service/team, sanitized request ID, status, and timing appear in the JSON request log.
def test_logging_contains_service_team_and_safe_request_context(service, supplied_id, monkeypatch):
    team = 'platform-team' if service == 'gateway' else f'{service}-team'
    monkeypatch.setenv('TEAM_NAME', team)
    records=[]
    class Capture(logging.Handler):
        def emit(self,record): records.append(json.loads(record.getMessage()))
    handler=Capture()
    logger.addHandler(handler)
    try:
        app=gateway.app if service == 'gateway' else make_app(service, Mock())
        response=TestClient(app).get('/health',headers={'x-request-id':supplied_id})
    finally:
        logger.removeHandler(handler)
    record=records[-1]
    assert record['service'] == service
    assert record['team'] == team
    assert record['request_id'] == response.headers['x-request-id']
    if supplied_id == 'test-request-123':
        assert record['request_id'] == supplied_id
    else:
        assert record['request_id'] != supplied_id
    assert record['path'] == '/health' and record['method'] == 'GET'
    assert record['status'] == 200 and record['duration_ms'] >= 0
