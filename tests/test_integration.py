# Brings in the libraries, shared code, and test or runtime settings needed below.
from unittest.mock import Mock
import httpx
import pytest
from fastapi.testclient import TestClient
from apps.gateway import main as gateway
from apps.services.fraud.main import app as fraud
from apps.services.forecasting.main import app as forecasting
from apps.services.recommendations.main import app as recommendations
from apps.services.common.api import create_app
from apps.services.common.inference import InferenceEngine
from apps.services.common.schemas import Transaction, FraudResponse
from apps.services.common.sagemaker_adapter import RuntimeFailure

APPS = {'fraud': fraud, 'forecasting': forecasting, 'recommendations': recommendations}

@pytest.mark.parametrize('service,payload', [('fraud', {'amount': -1, 'transaction_count': 1, 'account_age_days': 1}),
 ('forecasting', {'values': [], 'periods': 3}), ('forecasting', {'values': [1], 'periods': 0}),
 ('recommendations', {'user_id': 1, 'category': 'electronics', 'limit': -1}),
 ('recommendations', {'user_id': 1, 'category': 'unknown'})])
# Checks malformed business requests return 422.
def test_validation(service, payload):
    assert TestClient(APPS[service]).post('/predict', json=payload).status_code == 422

# Checks that a missing artifact leaves the process alive but makes readiness and prediction fail
# safely.
def test_missing_artifact_liveness():
    engine = InferenceEngine('fraud', model_path='/missing/model.joblib')
    client = TestClient(create_app('fraud', Transaction, FraudResponse, engine))
    assert client.get('/health').status_code == 200
    assert client.get('/ready').status_code == 503
    assert client.post('/predict', json={'amount': 1, 'transaction_count': 1, 'account_age_days': 1}).status_code == 503

# Checks that failed remote inference returns an error instead of silently using a local model.
def test_sagemaker_failure_never_falls_back():
    adapter = Mock()
    adapter.is_configured.return_value = True
    adapter.invoke.side_effect = RuntimeFailure('private error')
    engine = InferenceEngine('fraud', provider='sagemaker', adapter=adapter)
    client = TestClient(create_app('fraud', Transaction, FraudResponse, engine))
    response = client.post('/predict', json={'amount': 1, 'transaction_count': 1, 'account_age_days': 1})
    assert response.status_code == 502
    assert 'private' not in response.text
    adapter.invoke.assert_called_once()

# Checks valid remote output is labeled SageMaker and invalid scores are rejected.
def test_sagemaker_success_and_invalid_output():
    adapter = Mock()
    adapter.is_configured.return_value = True
    engine = InferenceEngine('fraud', provider='sagemaker', adapter=adapter)
    client = TestClient(create_app('fraud', Transaction, FraudResponse, engine))
    adapter.invoke.return_value = {'prediction': 'fraud', 'risk_score': 0.9, 'model': 'remote-v1'}
    payload = {'amount': 1, 'transaction_count': 1, 'account_age_days': 1}
    assert client.post('/predict', json=payload).json() == {'prediction': 'fraud', 'risk_score': 0.9, 'model': 'remote-v1', 'provider': 'sagemaker'}
    adapter.invoke.return_value = {'prediction': 'fraud', 'risk_score': 99, 'model': 'remote-v1'}
    assert client.post('/predict', json=payload).status_code == 502
    adapter.is_configured.return_value = False
    assert client.get('/ready').status_code == 503

# Checks that the newest history value becomes lag 1 and each forecast updates the next
# prediction’s history.
def test_forecast_lag_order():
    engine = InferenceEngine('forecasting')
    engine.model = Mock()
    engine.model.predict.return_value = [40]
    result = engine.predict({'values': [10,20,30], 'periods': 2})
    assert engine.model.predict.call_args_list[0].args[0].iloc[0].tolist() == [30,20,10]
    assert engine.model.predict.call_args_list[1].args[0].iloc[0].tolist() == [40,30,20]
    assert result['forecast'] == [40,40]

# Checks catalog-wide category/item encoding and ranking by predicted click probability.
def test_recommendation_encoding_and_probability():
    engine = InferenceEngine('recommendations')
    engine.model = Mock()
    engine.model.classes_ = [0,1]
    import numpy as np
    def score(features):
        assert features.item_id.nunique() > 1
        assert features.category.unique().tolist() == [engine.categories.index('electronics')]
        return np.array([[0.1,0.9] for _ in range(len(features))])
    engine.model.predict_proba.side_effect = score
    result = engine.predict({'user_id': 12, 'category': 'electronics', 'limit': 2})
    assert all(item['score'] == 0.9 for item in result['recommendations'])

@pytest.mark.parametrize('service,payload,key', [('fraud', {'amount':1800,'transaction_count':35,'account_age_days':12}, 'risk_score'),
 ('forecasting', {'values':[10,20,30],'periods':2}, 'forecast'),
 ('recommendations', {'user_id':12,'category':'electronics','limit':2}, 'recommendations')])
# Connects the gateway to real local service apps in memory, proving route-to-model integration
# without an AWS/network dependency.
def test_gateway_to_real_model(monkeypatch, service, payload, key):
    # Sends one HTTP request to a downstream API using an explicit timeout.
    async def downstream(method, url, **kwargs):
        assert url == gateway.SERVICE_URLS[service] + '/predict'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=APPS[service]), base_url='http://service') as client:
            return await client.request(method, '/predict', **kwargs)
    monkeypatch.setattr(gateway, 'downstream', downstream)
    response = TestClient(gateway.app).post(f'/{service}/predict', json=payload)
    assert response.status_code == 200
    assert response.json()['provider'] == 'local'
    assert key in response.json()
