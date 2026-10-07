# Brings in the libraries, shared code, and test or runtime settings needed below.
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from apps.services.common.inference import InferenceEngine
from apps.services.common.sagemaker_adapter import SageMakerRuntimeAdapter
from apps.services.common.api import create_app
from apps.services.common.schemas import Transaction, FraudResponse, ForecastRequest, ForecastResponse, RecommendationRequest, RecommendationResponse

CONTRACTS={'fraud':(Transaction,FraudResponse),'forecasting':(ForecastRequest,ForecastResponse),'recommendations':(RecommendationRequest,RecommendationResponse)}

@pytest.mark.parametrize('service', CONTRACTS)
# Checks all metadata values match configuration and no inference request is made.
def test_metadata_reports_actual_configuration_without_invoking_aws(monkeypatch,service):
    monkeypatch.setenv('TEAM_NAME',service+'-team')
    monkeypatch.setenv('MODEL_NAME',service+'-model-v1')
    monkeypatch.setenv('MODEL_VERSION','v1')
    monkeypatch.setenv('SERVICE_VERSION','tested-release')
    runtime=Mock()
    adapter=SageMakerRuntimeAdapter(service,'us-east-1',service+'-endpoint',runtime)
    app=create_app(service,*CONTRACTS[service],engine=InferenceEngine(service,provider='sagemaker',adapter=adapter))
    response=TestClient(app).get('/metadata')
    assert response.status_code==200
    assert response.json()=={'service':service,'team':service+'-team','model':service+'-model-v1','model_version':'v1','service_version':'tested-release','provider':'sagemaker','endpoint':service+'-endpoint','region':'us-east-1'}
    runtime.invoke_endpoint.assert_not_called()

# Checks configuration information remains readable even when inference readiness fails.
def test_metadata_remains_available_when_runtime_is_not_ready(monkeypatch):
    for key in ['AWS_REGION','FRAUD_SAGEMAKER_ENDPOINT','TEAM_NAME','MODEL_VERSION','SERVICE_VERSION']:
        monkeypatch.delenv(key,raising=False)
    adapter=SageMakerRuntimeAdapter('fraud',client=Mock())
    app=create_app('fraud',*CONTRACTS['fraud'],engine=InferenceEngine('fraud',provider='sagemaker',adapter=adapter))
    client=TestClient(app)
    assert client.get('/ready').status_code==503
    metadata=client.get('/metadata').json()
    assert metadata['endpoint'] is None and metadata['region'] is None
    assert metadata['team'] is None and metadata['service_version'] is None
    adapter.client.invoke_endpoint.assert_not_called()
