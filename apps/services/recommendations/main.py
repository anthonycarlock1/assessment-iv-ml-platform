# This file is the recommendation API.
# It helps suggest products or items based on a user and category.
# In a beginner explanation: "This service ranks items from best match to worst match."

import logging
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apps.services.common.sagemaker_adapter import get_runtime_adapter

# Resolve the model path for both local repository execution and container execution.
MODEL_FILE = 'recommendations_model.joblib'
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
logger = logging.getLogger('recommendations-service')
runtime_adapter = get_runtime_adapter('recommendations')

app = FastAPI(
    title='Recommendations Service',
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


# Request format for a recommendation request.
class RecommendationRequest(BaseModel):
    user_id: int
    category: str
    limit: int = 3


# Simple health endpoint for checks.
@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'recommendations',
    }


# Polling check to confirm the service is ready.
@app.get('/ready')
def ready():
    return {
        'status': 'ready',
        'model_loaded': MODEL_PATH.exists(),
    }


def _local_predict(request: RecommendationRequest):
    category_code = pd.Series([request.category]).astype('category').cat.codes.iloc[0]
    candidate_items = [
        'item-001', 'item-002', 'item-003', 'item-004', 'item-005',
        'item-006', 'item-007', 'item-008', 'item-009', 'item-010',
    ]

    scored = []
    for item in candidate_items:
        item_code = pd.Series([item]).astype('category').cat.codes.iloc[0]
        features = pd.DataFrame([
            {'user_id': request.user_id, 'category': category_code, 'item_id': item_code}
        ])
        prediction = model.predict(features)[0]
        scored.append({
            'item_id': item,
            'category': request.category,
            'score': round(float(prediction), 4),
        })

    scored = sorted(scored, key=lambda x: x['score'], reverse=True)[:request.limit]

    return {
        'user_id': request.user_id,
        'recommendations': scored,
        'model': 'recommendations-model-v1',
    }


# Main recommendation logic.
@app.post('/predict')
def predict(request: RecommendationRequest):
    logger.info('recommendations.predict.request', extra={'user_id': request.user_id, 'category': request.category})

    if runtime_adapter.is_configured():
        try:
            return runtime_adapter.invoke({
                'user_id': request.user_id,
                'category': request.category,
                'limit': request.limit,
            })
        except Exception as exc:
            logger.warning('recommendations.predict.adapter_failed', extra={'error': str(exc)})

    return _local_predict(request)
