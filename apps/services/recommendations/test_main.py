import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app


class RecommendationsModelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')

    def test_predict_returns_recommendations(self):
        response = self.client.post(
            '/predict',
            json={
                'user_id': 12,
                'category': 'electronics',
                'limit': 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['user_id'], 12)
        self.assertEqual(payload['model'], 'recommendations-model-v1')
        self.assertLessEqual(len(payload['recommendations']), 3)
        self.assertGreater(len(payload['recommendations']), 0)


if __name__ == '__main__':
    unittest.main()
