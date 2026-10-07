# Brings in the libraries, shared code, and test or runtime settings needed below.
import pytest
from fastapi.testclient import TestClient
from ml.serving.main import create_serving_app
from apps.services.common.inference import InferenceEngine

@pytest.mark.parametrize('service,payload,key', [
 ('fraud', {'amount':1800,'transaction_count':35,'account_age_days':12}, 'risk_score'),
 ('forecasting', {'values':[10,20,30],'periods':2}, 'forecast'),
 ('recommendations', {'user_id':12,'category':'electronics','limit':2}, 'recommendations')])
# Checks /ping and /invocations behave correctly, and hosted output matches direct model output.
def test_hosting_contract(service, payload, key):
    client = TestClient(create_serving_app(service))
    assert client.get('/ping').status_code == 200
    assert client.post('/ping').status_code == 200
    hosted = client.post('/invocations', json=payload)
    direct = client.post('/predict', json=payload)
    assert hosted.status_code == 200
    assert hosted.json() == direct.json()
    assert key in hosted.json()
    assert client.post('/invocations', json={}).status_code == 422

# Checks that an unavailable artifact makes SageMaker’s ping fail.
def test_ping_checks_artifact():
    engine = InferenceEngine('fraud', model_path='/missing.joblib')
    assert TestClient(create_serving_app('fraud', engine)).get('/ping').status_code == 503
