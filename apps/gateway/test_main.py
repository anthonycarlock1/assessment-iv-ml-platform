# Brings in the libraries, shared code, and test or runtime settings needed below.
from unittest.mock import AsyncMock
import httpx
import pytest
from fastapi.testclient import TestClient
from apps.gateway import main

@pytest.mark.parametrize('service', list(main.SERVICE_URLS))
@pytest.mark.parametrize('path', ['predict', 'health', 'ready', 'metadata'])
# Checks every service/path combination and proves exactly one call went to the intended
# downstream URL, carrying the request ID.
def test_route_targets_only_correct_service(monkeypatch, service, path):
    body = {'prediction': 'legitimate', 'risk_score': 0.1} if path == 'predict' else {'status': 'ready'}
    mock = AsyncMock(return_value=httpx.Response(200, json=body))
    monkeypatch.setattr(main, 'downstream', mock)
    client = TestClient(main.app)
    response = client.post(f'/{service}/{path}', json={'test': 1}) if path == 'predict' else client.get(f'/{service}/{path}')
    assert response.json() == body
    mock.assert_awaited_once()
    assert mock.call_args.args == ('POST' if path == 'predict' else 'GET', main.SERVICE_URLS[service] + '/' + path)
    assert mock.call_args.kwargs['headers']['x-request-id'] == response.headers['x-request-id']

@pytest.mark.parametrize('status,expected', [(422,422), (500,502)])
# Checks that input errors keep the appropriate status and backend failures become safe gateway
# errors.
def test_downstream_errors(monkeypatch, status, expected):
    monkeypatch.setattr(main, 'downstream', AsyncMock(return_value=httpx.Response(status, json={'detail': 'bad input' if status == 422 else 'secret stack'})))
    response = TestClient(main.app).post('/fraud/predict', json={})
    assert response.status_code == expected
    assert 'secret' not in response.text

# Checks gateway liveness, all-service readiness, and safe errors when downstream connections
# fail.
def test_health_and_readiness(monkeypatch):
    client = TestClient(main.app)
    assert client.get('/health').status_code == 200
    mock = AsyncMock(return_value=httpx.Response(200, json={'status': 'ready'}))
    monkeypatch.setattr(main, 'downstream', mock)
    assert client.get('/ready').status_code == 200
    assert mock.await_count == 3
    monkeypatch.setattr(main, 'downstream', AsyncMock(side_effect=httpx.ConnectError('private hostname')))
    assert client.get('/ready').status_code == 503
    response = client.post('/fraud/predict', json={})
    assert response.status_code == 502
    assert 'private hostname' not in response.text
