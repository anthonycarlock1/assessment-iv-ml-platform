# Brings in the libraries, shared code, and test or runtime settings needed below.
"""SageMaker hosting contract using the existing trained artifact engine."""
import os
from fastapi import HTTPException
from apps.services.common.api import create_app
from apps.services.common.inference import InferenceEngine
from apps.services.common.schemas import (
    Transaction, FraudResponse, ForecastRequest, ForecastResponse,
    RecommendationRequest, RecommendationResponse,
)

# Chooses the right request and response schema for each model.
CONTRACTS = {
    'fraud': (Transaction, FraudResponse),
    'forecasting': (ForecastRequest, ForecastResponse),
    'recommendations': (RecommendationRequest, RecommendationResponse),
}

# Selects the request/response contracts, forces real local model execution inside the hosting
# container, and adds SageMaker’s required routes.
def create_serving_app(service, engine=None):
    request_model, response_model = CONTRACTS[service]
    # Hosting must run inference itself, never invoke another SageMaker endpoint.
    engine = engine or InferenceEngine(service, provider='local')
    app = create_app(service, request_model, response_model, engine)
    predict = next(route.endpoint for route in app.routes if route.path == '/predict')
    # Reuses prediction handling under SageMaker’s /invocations path.
    app.post('/invocations', response_model=response_model)(predict)

    @app.api_route('/ping', methods=['GET', 'POST'])
    # Reports whether the hosted artifact is loaded, so SageMaker can check container readiness.
    def ping():
        if not app.state.engine.ready():
            raise HTTPException(503, 'Model unavailable')
        return {'status': 'ready', 'service': service}
    return app

# Chooses the model from SERVICE_NAME; the default is fraud.
app = create_serving_app(os.environ.get('SERVICE_NAME', 'fraud'))
