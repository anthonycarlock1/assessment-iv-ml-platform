import json
import time
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from apps.services.common.api import create_app
from apps.services.common.history import PredictionHistory
from apps.services.common.schemas import Transaction, FraudResponse


@pytest.fixture
def history(monkeypatch):
    monkeypatch.setenv('PREDICTION_HISTORY_ENABLED', 'true')
    monkeypatch.setenv('PREDICTION_HISTORY_TABLE', 'test-history')
    return PredictionHistory('fraud', client=Mock())


def test_round_trip_float_payload_and_service_partition(history):
    payload = {'amount': 123.45}
    result = {'risk_score': 0.76, 'provider': 'sagemaker'}
    history.save('request-123', payload, result)
    item = history.client.put_item.call_args.kwargs['Item']
    assert json.loads(item['payload']['S']) == payload
    assert json.loads(item['result']['S']) == result
    assert item['service'] == {'S': 'fraud'}
    assert int(item['expires_at']['N']) > time.time() + 29 * 86400
    history.client.query.return_value = {'Items': [item]}
    assert history.recent(10)['items'][0]['result'] == result
    assert history.client.query.call_args.kwargs['ExpressionAttributeValues'] == {':service': {'S': 'fraud'}}
    assert history.client.query.call_args.kwargs['ScanIndexForward'] is False


def test_expired_rows_are_hidden_and_duplicate_request_ids_do_not_overwrite(history):
    history.save('same-id', {}, {})
    first = history.client.put_item.call_args.kwargs['Item']
    history.save('same-id', {}, {})
    second = history.client.put_item.call_args.kwargs['Item']
    assert first['event_id'] != second['event_id']
    first['expires_at'] = {'N': '1'}
    history.client.query.return_value = {'Items': [first, second]}
    assert len(history.recent(10)['items']) == 1


def test_disabled_history_never_calls_aws(monkeypatch):
    monkeypatch.setenv('PREDICTION_HISTORY_ENABLED', 'false')
    store = PredictionHistory('fraud', client=Mock())
    store.save('id', {}, {})
    assert store.recent(10) == {'enabled': False, 'items': []}
    assert not store.client.mock_calls


def test_storage_outage_preserves_predictions_and_readiness(history):
    engine = Mock(provider='sagemaker')
    engine.ready.return_value = True
    engine.predict.return_value = {'model': 'fraud-model-v1', 'provider': 'sagemaker',
                                   'prediction': 'fraud', 'risk_score': 0.76}
    app = create_app('fraud', Transaction, FraudResponse, engine=engine)
    app.state.history = history
    history.client.put_item.side_effect = RuntimeError('private AWS error')
    history.client.query.side_effect = RuntimeError('private AWS error')
    client = TestClient(app)
    response = client.post('/predict', json={'amount': 123.45, 'transaction_count': 1,
                                            'account_age_days': 2})
    assert response.status_code == 200
    assert response.json()['risk_score'] == 0.76
    assert client.get('/ready').status_code == 200
    assert client.get('/history').json() == {'detail': 'Prediction history unavailable'}
    assert client.get('/history?limit=51').status_code == 422
    assert client.post('/predict', json={'amount': -1}).status_code == 422
    assert history.client.put_item.call_count == 1


@pytest.mark.parametrize('service', ['fraud', 'forecasting', 'recommendations'])
def test_gateway_history_routes_are_service_specific(monkeypatch, service):
    import httpx
    from apps.gateway import main
    calls = []
    async def downstream(method, url, **kwargs):
        calls.append((method, url))
        return httpx.Response(200, json={'enabled': True, 'items': []})
    monkeypatch.setattr(main, 'downstream', downstream)
    response = TestClient(main.app).get(f'/{service}/history?limit=5')
    assert response.status_code == 200
    assert calls == [('GET', main.SERVICE_URLS[service] + '/history?limit=5')]
    assert TestClient(main.app).get(f'/{service}/history?limit=0').status_code == 422
