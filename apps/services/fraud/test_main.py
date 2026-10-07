# Brings in the libraries, shared code, and test or runtime settings needed below.
from fastapi.testclient import TestClient
from apps.services.fraud.main import app

client = TestClient(app)

# Checks that the service is alive and its local test model is ready.
def test_health_and_ready():
    assert client.get('/health').json() == {'status': 'healthy', 'service': 'fraud'}
    assert client.get('/ready').status_code == 200

# Runs the saved model and checks meaningful values, labels, counts, or ranking rather than just
# HTTP 200.
def test_real_prediction():
    response = client.post('/predict', json={'amount': 1800, 'transaction_count': 35, 'account_age_days': 12})
    assert response.status_code == 200
    result = response.json()
    assert result['provider'] == 'local'
    assert result['model'] == 'fraud-model-v1'
    assert result['prediction'] == 'fraud'
    assert result['risk_score'] > 0.5
