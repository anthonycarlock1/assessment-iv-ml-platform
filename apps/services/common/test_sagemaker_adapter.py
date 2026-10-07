# Brings in the libraries, shared code, and test or runtime settings needed below.
from io import BytesIO
from unittest.mock import Mock, patch
import pytest
from botocore.exceptions import ClientError
from apps.services.common.sagemaker_adapter import SageMakerRuntimeAdapter, RuntimeFailure

# Checks that endpoint/region come from configuration and that a supplied fake AWS client receives
# the expected JSON request.
def test_environment_and_injected_runtime(monkeypatch):
    monkeypatch.setenv('AWS_REGION', 'us-east-1')
    monkeypatch.setenv('FRAUD_SAGEMAKER_ENDPOINT', 'existing-endpoint')
    runtime = Mock()
    runtime.invoke_endpoint.return_value = {'Body': BytesIO(b'{"prediction":"fraud"}')}
    adapter = SageMakerRuntimeAdapter('fraud', client=runtime)
    assert adapter.invoke({'amount': 10}) == {'prediction': 'fraud'}
    runtime.invoke_endpoint.assert_called_once_with(EndpointName='existing-endpoint', ContentType='application/json', Accept='application/json', Body=b'{"amount": 10}')

# Checks that missing critical runtime configuration prevents invocation.
def test_requires_endpoint_and_region(monkeypatch):
    monkeypatch.delenv('AWS_REGION', raising=False)
    monkeypatch.delenv('FRAUD_SAGEMAKER_ENDPOINT', raising=False)
    monkeypatch.setenv('MODEL_PROVIDER', 'sagemaker')
    adapter = SageMakerRuntimeAdapter('fraud')
    assert not adapter.is_configured()
    with pytest.raises(RuntimeFailure): adapter.invoke({})

# Checks the explicit AWS connect/read timeout settings.
def test_client_timeouts():
    with patch('apps.services.common.sagemaker_adapter.boto3.client') as factory:
        adapter = SageMakerRuntimeAdapter('fraud', 'us-east-1', 'endpoint')
        adapter.client
        config = factory.call_args.kwargs['config']
        assert config.connect_timeout == 3
        assert config.read_timeout == 70
        assert config.retries['total_max_attempts'] == 1

@pytest.mark.parametrize('bad', [b'not-json', b'[]'])
# Rejects malformed JSON and non-object runtime responses.
def test_invalid_runtime_response(bad):
    client = Mock()
    client.invoke_endpoint.return_value = {'Body': BytesIO(bad)}
    with pytest.raises(RuntimeFailure): SageMakerRuntimeAdapter('fraud', 'us-east-1', 'endpoint', client).invoke({})

# Checks that an AWS failure becomes a safe runtime exception.
def test_aws_failure_wrapped():
    client = Mock()
    client.invoke_endpoint.side_effect = ClientError({'Error': {'Code': 'AccessDenied', 'Message': 'secret'}}, 'InvokeEndpoint')
    with pytest.raises(RuntimeFailure, match='Inference runtime failed'):
        SageMakerRuntimeAdapter('fraud', 'us-east-1', 'endpoint', client).invoke({})


# Checks the logged error fields and confirms private AWS messages are omitted.
def test_failure_log_is_structured_and_does_not_leak_aws_message(monkeypatch):
    import json
    monkeypatch.setenv('TEAM_NAME','forecasting-team')
    client=Mock()
    client.invoke_endpoint.side_effect=ClientError({'Error':{'Code':'ModelNotReadyException','Message':'private runtime detail'}},'InvokeEndpoint')
    with patch('apps.services.common.sagemaker_adapter.logging.getLogger') as logger:
        with pytest.raises(RuntimeFailure):
            SageMakerRuntimeAdapter('forecasting','us-east-1','endpoint',client).invoke({})
    record=json.loads(logger.return_value.error.call_args.args[0])
    assert record['event']=='inference_runtime_failure'
    assert record['service']=='forecasting' and record['team']=='forecasting-team'
    assert record['aws_error_code']=='ModelNotReadyException'
    assert 'private runtime detail' not in str(record)


@pytest.mark.parametrize('code,status',[('ModelError',0),('ModelNotReadyException',None)])
# Simulates a fast transient failure followed by success and checks the returned forecast values
# and identical retry payload.
def test_fast_unavailable_model_retries_once_and_returns_semantic_output(code,status):
    client=Mock()
    client.invoke_endpoint.side_effect=[ClientError({'Error':{'Code':code},'OriginalStatusCode':status},'InvokeEndpoint'),
        {'Body':BytesIO(b'{"forecast":[109.85,109.77],"periods":2}')}]
    with patch('apps.services.common.sagemaker_adapter.time.sleep') as sleep:
        result=SageMakerRuntimeAdapter('forecasting','us-east-1','endpoint',client).invoke({'values':[10,20,30],'periods':2})
    assert result == {'forecast':[109.85,109.77],'periods':2}
    assert client.invoke_endpoint.call_count == 2
    assert client.invoke_endpoint.call_args_list[0] == client.invoke_endpoint.call_args_list[1]
    sleep.assert_called_once_with(0.25)

# Checks that a slow failure does not trigger an extra request beyond the gateway budget.
def test_slow_unavailable_model_does_not_retry_past_gateway_budget():
    client=Mock()
    client.invoke_endpoint.side_effect=ClientError({'Error':{'Code':'ModelError'},'OriginalStatusCode':0},'InvokeEndpoint')
    with patch('apps.services.common.sagemaker_adapter.time.monotonic',side_effect=[0,2]):
        with pytest.raises(RuntimeFailure):
            SageMakerRuntimeAdapter('forecasting','us-east-1','endpoint',client).invoke({})
    client.invoke_endpoint.assert_called_once()

# Checks that repeated unavailability stops after two attempts.
def test_model_unavailable_retry_is_bounded():
    client=Mock()
    client.invoke_endpoint.side_effect=ClientError({'Error':{'Code':'ModelError'},'OriginalStatusCode':0},'InvokeEndpoint')
    with patch('apps.services.common.sagemaker_adapter.time.sleep'):
        with pytest.raises(RuntimeFailure):
            SageMakerRuntimeAdapter('forecasting','us-east-1','endpoint',client).invoke({})
    assert client.invoke_endpoint.call_count == 2
