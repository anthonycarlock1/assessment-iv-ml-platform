# Brings in the libraries, shared code, and test or runtime settings needed below.
from fastapi.testclient import TestClient
from apps.services.forecasting.main import app

client = TestClient(app)

# Checks that the service is alive and its local test model is ready.
def test_health_and_ready():
    assert client.get('/health').json() == {'status': 'healthy', 'service': 'forecasting'}
    assert client.get('/ready').status_code == 200

# Runs the saved model and checks meaningful values, labels, counts, or ranking rather than just
# HTTP 200.
def test_real_prediction():
    response = client.post('/predict', json={'values': [100,102,101,105,110,108], 'periods': 3})
    assert response.status_code == 200
    result = response.json()
    assert result['provider'] == 'local'
    assert result['model'] == 'forecasting-model-v1'
    assert result['periods'] == 3
    assert len(result['forecast']) == 3
    assert all(value > 0 for value in result['forecast'])
