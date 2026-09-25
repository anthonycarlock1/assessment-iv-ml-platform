import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app


class ForecastingModelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')

    def test_predict_returns_forecast(self):
        response = self.client.post(
            '/predict',
            json={
                'values': [100, 102, 101, 105, 110, 108],
                'periods': 3,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['periods'], 3)
        self.assertEqual(payload['model'], 'forecasting-model-v1')
        self.assertGreater(len(payload['forecast']), 0)


if __name__ == '__main__':
    unittest.main()
