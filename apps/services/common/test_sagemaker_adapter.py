import os
import unittest
from unittest.mock import MagicMock, patch

from apps.services.common.sagemaker_adapter import SageMakerRuntimeAdapter, get_runtime_adapter


class SageMakerAdapterTests(unittest.TestCase):
    def test_reads_endpoint_and_region_from_environment(self):
        with patch.dict(os.environ, {'AWS_REGION': 'us-west-2', 'FRAUD_SAGEMAKER_ENDPOINT': 'fraud-test-endpoint'}, clear=False):
            adapter = get_runtime_adapter('fraud')
            self.assertEqual(adapter.region_name, 'us-west-2')
            self.assertEqual(adapter.endpoint_name, 'fraud-test-endpoint')

    @patch('boto3.client')
    def test_invoke_calls_runtime_endpoint(self, mock_client):
        mock_runtime = MagicMock()
        mock_runtime.invoke_endpoint.return_value = {'Body': MagicMock()}
        mock_client.return_value = mock_runtime

        body = MagicMock()
        body.read.return_value = b'{"prediction": "legitimate"}'
        mock_runtime.invoke_endpoint.return_value['Body'] = body

        adapter = SageMakerRuntimeAdapter('fraud', 'us-east-1', 'fraud-test-endpoint')
        payload = adapter.invoke({'amount': 100.0, 'transaction_count': 2, 'account_age_days': 30})

        self.assertEqual(payload['prediction'], 'legitimate')
        mock_runtime.invoke_endpoint.assert_called_once()


if __name__ == '__main__':
    unittest.main()
