from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / 'ml' / 'models' / 'recommendations_model.joblib'

model = joblib.load(MODEL_PATH)

app = FastAPI(
    title='Recommendations Service',
    version='1.0.0',
)


class RecommendationRequest(BaseModel):
    user_id: int
    category: str
    limit: int = 3


@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'recommendations',
    }


@app.get('/ready')
def ready():
    return {
        'status': 'ready',
        'model_loaded': MODEL_PATH.exists(),
    }


@app.post('/predict')
def predict(request: RecommendationRequest):
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
