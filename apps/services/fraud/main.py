# This file is the fraud detection API.
# It is a small web service that takes transaction data and returns a risk result.
# In a presentation, say: "This service listens for requests and uses a model to decide if something looks suspicious."

import logging
from pathlib import Path

import joblib
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.services.common.sagemaker_adapter import get_runtime_adapter

# Resolve the model path for both local repository execution and container execution.
MODEL_FILE = 'fraud_model.joblib'
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

# Load the model once when the app starts.
model = joblib.load(MODEL_PATH)
logger = logging.getLogger('fraud-service')
runtime_adapter = get_runtime_adapter('fraud')

app = FastAPI(
    title='Fraud Detection Service',
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


# This tells FastAPI what data the request should contain.
class Transaction(BaseModel):
    amount: float
    transaction_count: int
    account_age_days: int


# Health check endpoint.
# Used by Kubernetes to see if the service is alive.
@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'fraud-detection',
    }


# Readiness check endpoint.
# Used to confirm the service is ready to receive traffic.
@app.get('/ready')
def ready():
    return {
        'status': 'ready',
        'model_loaded': MODEL_PATH.exists(),
    }


def _local_predict(transaction: Transaction):
    features = [[transaction.amount, transaction.transaction_count, transaction.account_age_days]]
    predicted_label = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1]
    return {
        'prediction': 'fraud' if predicted_label == 1 else 'legitimate',
        'risk_score': round(float(probability), 4),
        'model': 'fraud-model-v1',
    }


# Main prediction endpoint.
# The app receives transaction details and returns a fraud/legitimate prediction.
@app.post('/predict')
def predict(transaction: Transaction):
    logger.info('fraud.predict.request', extra={'amount': transaction.amount, 'transaction_count': transaction.transaction_count})

    if runtime_adapter.is_configured():
        try:
            payload = {
                'amount': transaction.amount,
                'transaction_count': transaction.transaction_count,
                'account_age_days': transaction.account_age_days,
            }
            return runtime_adapter.invoke(payload)
        except Exception as exc:  # pragma: no cover - falls back for local demo reliability
            logger.warning('fraud.predict.adapter_failed', extra={'error': str(exc)})

    return _local_predict(transaction)
