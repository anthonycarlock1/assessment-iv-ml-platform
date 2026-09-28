from pathlib import Path
from typing import List

import joblib
from fastapi import FastAPI
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / 'ml' / 'models' / 'forecasting_model.joblib'

model = joblib.load(MODEL_PATH)

app = FastAPI(
    title='Forecasting Service',
    version='1.0.0',
)


class ForecastRequest(BaseModel):
    values: List[float]
    periods: int = 3


@app.get('/health')
def health():
    return {
        'status': 'healthy',
        'service': 'forecasting',
    }


@app.get('/ready')
def ready():
    return {
        'status': 'ready',
        'model_loaded': MODEL_PATH.exists(),
    }


@app.post('/predict')
def predict(request: ForecastRequest):
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
