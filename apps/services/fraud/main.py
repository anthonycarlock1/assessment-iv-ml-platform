from pathlib import Path

import joblib
from fastapi import FastAPI
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / 'ml' / 'models' / 'fraud_model.joblib'

model = joblib.load(MODEL_PATH)

app = FastAPI(
    title='Fraud Detection Service',
    version='1.0.0',
)


class Transaction(BaseModel):
    amount: float
    transaction_count: int
    account_age_days: int


@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'fraud-detection',
    }


@app.get('/ready')
def ready():
    return {
        'status': 'ready',
        'model_loaded': MODEL_PATH.exists(),
    }


@app.post('/predict')
def predict(transaction: Transaction):
    features = [[transaction.amount, transaction.transaction_count, transaction.account_age_days]]
    predicted_label = model.predict(features)[0]
    probability = model.predict_proba(features)[0][1]

    return {
        'prediction': 'fraud' if predicted_label == 1 else 'legitimate',
        'risk_score': round(float(probability), 4),
        'model': 'fraud-model-v1',
    }
