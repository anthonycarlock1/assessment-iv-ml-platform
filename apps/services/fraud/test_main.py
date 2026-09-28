import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import app


class FraudModelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'healthy')

    def test_predict_uses_real_model(self):
        response = self.client.post(
            '/predict',
            json={
                'amount': 1800.0,
                'transaction_count': 35,
                'account_age_days': 12,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('prediction', payload)
        self.assertIn('risk_score', payload)
        self.assertEqual(payload['model'], 'fraud-model-v1')
        self.assertIn(payload['prediction'], ['fraud', 'legitimate'])


if __name__ == '__main__':
    unittest.main()
