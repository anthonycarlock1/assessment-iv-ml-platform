# Brings in the libraries, shared code, and test or runtime settings needed below.
import time
import logging
import json
import os
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

# Represents an inference-runtime problem without exposing the original AWS details to the caller.
class RuntimeFailure(Exception):
    pass

# Distinguishes input rejected by the hosted model from an unavailable runtime.
class RuntimeInputRejected(RuntimeFailure):
    """The hosted model explicitly rejected the caller's input."""
    pass

# Wraps AWS invocation so tests can supply a fake client instead of calling AWS.
class SageMakerRuntimeAdapter:
    # Reads endpoint and region from arguments/environment and accepts an optional fake client.
    def __init__(self, service_name, region_name=None, endpoint_name=None, client=None):
        self.service_name = service_name
        self.region_name = region_name or os.getenv('AWS_REGION')
        self.endpoint_name = endpoint_name or os.getenv(f'{service_name.upper()}_SAGEMAKER_ENDPOINT')
        self._client = client

    # Checks that an endpoint name and AWS region are present.
    def is_configured(self):
        return bool(self.region_name and self.endpoint_name)

    @property
    # Creates the SageMaker Runtime client only when needed, with explicit connect/read timeouts
    # and automatic SDK retries disabled.
    def client(self):
        if self._client is None:
            self._client = boto3.client('sagemaker-runtime', region_name=self.region_name,
                config=Config(connect_timeout=3, read_timeout=70, retries={'total_max_attempts': 1}))
        return self._client

    # Writes a structured error event containing service/team, exception type, and AWS error code;
    # excludes raw AWS messages and stack traces.
    def log_failure(self, exc, aws_code=None):
        logging.getLogger('assessment').error(json.dumps({'event':'inference_runtime_failure',
            'service':self.service_name,'team':os.getenv('TEAM_NAME', 'fraud-team'),
            'exception_type':type(exc).__name__,'aws_error_code':aws_code}))

    # Sends the serialized request. Retries once after 250 ms only for a fast no-response/model-
    # not-ready failure; skips slow failures and ordinary request/permission errors.
    def invoke_with_retry(self, body):
        # Retry only a fast failure to obtain any model response. One short retry
        # keeps the existing 70s read timeout within the gateway's 75s budget.
        start = time.monotonic()
        for attempt in range(2):
            try:
                return self.client.invoke_endpoint(EndpointName=self.endpoint_name,
                    ContentType='application/json', Accept='application/json', Body=body)
            except ClientError as exc:
                error = exc.response
                code = error.get('Error', {}).get('Code')
                unavailable = (code == 'ModelNotReadyException' or
                    (code == 'ModelError' and error.get('OriginalStatusCode') == 0))
                if attempt or not unavailable or time.monotonic() - start >= 1:
                    raise
                logging.getLogger('assessment').warning(json.dumps({
                    'event':'inference_runtime_retry','service':self.service_name,
                    'team':os.getenv('TEAM_NAME', 'fraud-team'),'aws_error_code':code}))
                time.sleep(0.25)

    # Requires valid configuration, converts the payload to JSON, reads and closes the response
    # stream, and wraps invalid responses or AWS failures in safe exceptions.
    def invoke(self, payload):
        if not self.is_configured():
            raise RuntimeFailure('Runtime configuration missing')
        try:
            response = self.invoke_with_retry(json.dumps(payload, allow_nan=False).encode())
            stream = response['Body']
            try:
                result = json.loads(stream.read())
            finally:
                stream.close()
            if not isinstance(result, dict):
                raise ValueError('Expected object')
            return result
        except ClientError as exc:
            error = exc.response
            self.log_failure(exc, error.get('Error', {}).get('Code'))
            if (error.get('Error', {}).get('Code') == 'ModelError'
                    and error.get('OriginalStatusCode') in (400, 413, 415, 422)):
                raise RuntimeInputRejected('Inference input rejected') from exc
            raise RuntimeFailure('Inference runtime failed') from exc
        except (BotoCoreError, ValueError, KeyError, TypeError) as exc:
            self.log_failure(exc)
            raise RuntimeFailure('Inference runtime failed') from exc

# Creates a runtime adapter for the selected service, using optional region/endpoint arguments or
# environment settings.
def get_runtime_adapter(service_name, region_name=None, endpoint_name=None):
    return SageMakerRuntimeAdapter(service_name, region_name, endpoint_name)
