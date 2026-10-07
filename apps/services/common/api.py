# Brings in the libraries, shared code, and test or runtime settings needed below.
import os
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from pydantic import ValidationError
from apps.services.common.inference import InferenceEngine
from apps.services.common.observability import instrument
from apps.services.common.sagemaker_adapter import RuntimeFailure, RuntimeInputRejected

from apps.services.common.validation import install_validation_handler

# Defines the typed operational response: service, owning team, model/version, release, provider,
# endpoint, and region.
class ServiceMetadata(BaseModel):
    service: str
    team: Optional[str] = None
    model: str
    model_version: Optional[str] = None
    service_version: Optional[str] = None
    provider: str
    endpoint: Optional[str] = None
    region: Optional[str] = None


# Builds the shared FastAPI application, attaches the engine, and installs logging and validation
# handlers.
def create_app(service, request_model, response_model, engine=None):
    app = FastAPI(title=f'{service} inference service')
    app.state.engine = engine or InferenceEngine(service)
    instrument(app, service)
    install_validation_handler(app)

    @app.get('/metadata', response_model=ServiceMetadata)
    # Returns configured service/model information without invoking AWS. Missing values remain
    # missing rather than becoming demo data.
    def metadata():
        current = app.state.engine
        adapter = current.adapter if current.provider == 'sagemaker' else None
        return ServiceMetadata(service=service, team=os.getenv('TEAM_NAME'),
            model=os.getenv('MODEL_NAME', f'{service}-model-v1'),
            model_version=os.getenv('MODEL_VERSION'), service_version=os.getenv('SERVICE_VERSION'),
            provider=current.provider, endpoint=adapter.endpoint_name if adapter else None,
            region=adapter.region_name if adapter else None)

    @app.get('/health')
    # Returns process liveness. It does not invoke SageMaker or check the model service.
    def health():
        return {'status': 'healthy', 'service': service}

    @app.get('/ready')
    # Returns readiness only when required configuration or a local artifact is available;
    # otherwise returns 503.
    def ready():
        if not app.state.engine.ready():
            raise HTTPException(503, 'Inference configuration or model unavailable')
        return {'status': 'ready', 'service': service, 'provider': app.state.engine.provider}

    # Validates the engine result against the response model. It checks forecast length and
    # recommendation consistency, then maps bad input and downstream failures into safe HTTP
    # errors.
    def predict(payload):
        current = app.state.engine
        if not current.ready():
            raise HTTPException(503, 'Inference configuration or model unavailable')
        try:
            result = response_model.model_validate(current.predict(payload.model_dump()))
            if service == 'forecasting' and (result.periods != payload.periods or len(result.forecast) != payload.periods):
                raise RuntimeFailure('Invalid forecast response')
            if service == 'recommendations' and (result.user_id != payload.user_id or len(result.recommendations) > payload.limit):
                raise RuntimeFailure('Invalid recommendations response')
            return result
        except ValidationError:
            raise HTTPException(502, 'Invalid inference response')
        except RuntimeInputRejected:
            raise HTTPException(422, 'Inference input rejected; check request values')
        except RuntimeFailure:
            raise HTTPException(502, 'Inference runtime unavailable')
        except ValueError as exc:
            if current.provider == 'local' and service == 'recommendations':
                raise HTTPException(422, str(exc))
            raise HTTPException(502, 'Invalid inference response')
        except Exception:
            raise HTTPException(502, 'Inference runtime unavailable')

    # Attaches the service-specific request type to the common function and registers a typed
    # /predict response.
    predict.__annotations__ = {'payload': request_model}
    app.post('/predict', response_model=response_model)(predict)
    return app
