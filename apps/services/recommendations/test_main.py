# Brings in the libraries, shared code, and test or runtime settings needed below.
from fastapi.testclient import TestClient
from apps.services.recommendations.main import app

client = TestClient(app)

# Checks that the service is alive and its local test model is ready.
def test_health_and_ready():
    assert client.get('/health').json() == {'status': 'healthy', 'service': 'recommendations'}
    assert client.get('/ready').status_code == 200

# Runs the saved model and checks meaningful values, labels, counts, or ranking rather than just
# HTTP 200.
def test_real_prediction():
    response = client.post('/predict', json={'user_id': 12, 'category': 'electronics', 'limit': 3})
    assert response.status_code == 200
    result = response.json()
    assert result['provider'] == 'local'
    assert result['model'] == 'recommendations-model-v1'
    assert result['user_id'] == 12
    items = result['recommendations']
    assert len(items) == 2  # The catalog contains two electronics items.
    assert {i['item_id'] for i in items} == {'item-005', 'item-010'}
    assert items[0]['score'] > items[1]['score']
    assert [i['score'] for i in items] == sorted([i['score'] for i in items], reverse=True)
    assert all(i['category'] == 'electronics' and 0 <= i['score'] <= 1 for i in items)
