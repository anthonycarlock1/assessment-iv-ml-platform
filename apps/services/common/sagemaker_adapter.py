import json
import os
from typing import Any, Optional

import boto3


class SageMakerRuntimeAdapter:
    """Thin AWS SageMaker Runtime abstraction that keeps the app logic separate from AWS specifics."""

    def __init__(self, service_name: str, region_name: Optional[str] = None, endpoint_name: Optional[str] = None, client=None):
        self.service_name = service_name.lower()
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        env_key = f'{service_name.upper()}_SAGEMAKER_ENDPOINT'
        self.endpoint_name = endpoint_name or os.getenv(env_key) or os.getenv(f'{service_name.upper()}_MODEL_ENDPOINT')
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client('sagemaker-runtime', region_name=self.region_name)
        return self._client

    def is_configured(self) -> bool:
        provider = os.getenv('MODEL_PROVIDER', 'local').lower()
        return bool(self.endpoint_name) or provider != 'local'

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError(f'SageMaker endpoint is not configured for {self.service_name}.')

        response = self.client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload).encode('utf-8'),
        )
        body = response['Body'].read().decode('utf-8')
        return json.loads(body)


def get_runtime_adapter(service_name: str, region_name: Optional[str] = None, endpoint_name: Optional[str] = None):
    return SageMakerRuntimeAdapter(service_name, region_name=region_name, endpoint_name=endpoint_name)
