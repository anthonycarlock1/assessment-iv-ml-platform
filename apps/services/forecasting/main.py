# This file is the forecasting API.
# It uses past values to estimate what may happen next.
# In simple terms: "given recent numbers, predict the next few values."

import logging
from pathlib import Path
from typing import List

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.services.common.sagemaker_adapter import get_runtime_adapter

# Resolve the model path for both local repository execution and container execution.
MODEL_FILE = 'forecasting_model.joblib'
CANDIDATE_ROOTS = [
    Path(__file__).resolve().parents[3],
    Path(__file__).resolve().parents[2],
    Path(__file__).resolve().parent,
    Path('/app'),
]
MODEL_PATH = next(
    (root / 'ml' / 'models' / MODEL_FILE for root in CANDIDATE_ROOTS if (root / 'ml' / 'models' / MODEL_FILE).exists()),
    Path('/app') / 'ml' / 'models' / MODEL_FILE,
)

model = joblib.load(MODEL_PATH)
logger = logging.getLogger('forecasting-service')
runtime_adapter = get_runtime_adapter('forecasting')

app = FastAPI(
    title='Forecasting Service',
    version='1.0.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173',
        'http://127.0.0.1:5173',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# This is the incoming request format.
# The client sends a list of numbers and how many future points to forecast.
class ForecastRequest(BaseModel):
    values: List[float]
    periods: int = 3


# Health endpoint for Kubernetes.
@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'forecasting',
    }


# This tells Kubernetes the service is ready to accept traffic.
@app.get('/ready')
def ready():
    return {
        'status': 'ready',
        'model_loaded': MODEL_PATH.exists(),
    }


def _local_predict(request: ForecastRequest):
    if not request.values:
        return {
            'forecast': [],
            'periods': request.periods,
            'model': 'forecasting-model-v1',
        }

    history = list(request.values)
    forecast = []

    for _ in range(request.periods):
        pad = history[-3:]
        while len(pad) < 3:
            pad = [history[0]] + pad

        prediction = model.predict([pad])[0]
        forecast.append(round(float(prediction), 2))
        history.append(float(prediction))

    return {
        'forecast': forecast,
        'periods': request.periods,
        'model': 'forecasting-model-v1',
    }


# Main prediction endpoint.
@app.post('/predict')
def predict(request: ForecastRequest):
    logger.info('forecasting.predict.request', extra={'periods': request.periods, 'values_count': len(request.values)})

    if runtime_adapter.is_configured():
        try:
            return runtime_adapter.invoke({'values': request.values, 'periods': request.periods})
        except Exception as exc:
            logger.warning('forecasting.predict.adapter_failed', extra={'error': str(exc)})

    return _local_predict(request)
