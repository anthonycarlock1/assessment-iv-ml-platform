import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.gateway.main import app


class GatewayRoutingTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch('apps.gateway.main.httpx.post')
    def test_fraud_route_targets_fraud_service(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'prediction': 'legitimate', 'risk_score': 0.1}

        response = self.client.post('/fraud/predict', json={'amount': 10, 'transaction_count': 1, 'account_age_days': 20})

        self.assertEqual(response.status_code, 200)
        self.assertIn('fraud-service', mock_post.call_args[0][0])

    @patch('apps.gateway.main.httpx.post')
    def test_forecasting_route_targets_forecasting_service(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'forecast': [1.0, 2.0], 'periods': 2}

        response = self.client.post('/forecasting/predict', json={'values': [1, 2, 3], 'periods': 2})

        self.assertEqual(response.status_code, 200)
        self.assertIn('forecasting-service', mock_post.call_args[0][0])

    @patch('apps.gateway.main.httpx.post')
    def test_recommendations_route_targets_recommendations_service(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'recommendations': [{'item_id': 'item-001', 'score': 0.9}]}

        response = self.client.post('/recommendations/predict', json={'user_id': 1, 'category': 'electronics', 'limit': 1})

        self.assertEqual(response.status_code, 200)
        self.assertIn('recommendations-service', mock_post.call_args[0][0])


if __name__ == '__main__':
    unittest.main()
