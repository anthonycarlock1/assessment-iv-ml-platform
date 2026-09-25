from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI(
    title="Forecasting Service",
    version="1.0.0"
)


class ForecastRequest(BaseModel):
    values: List[float]
    periods: int = 3


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "forecasting"
    }


@app.get("/ready")
def ready():
    return {
        "status": "ready"
    }


@app.post("/predict")
def predict(request: ForecastRequest):
    if not request.values:
        return {
            "forecast": [],
            "model": "moving-average-placeholder-v1"
        }

    window = request.values[-min(3, len(request.values)):]
    prediction = sum(window) / len(window)

    forecast = [
        round(prediction, 2)
        for _ in range(request.periods)
    ]

    return {
        "forecast": forecast,
        "periods": request.periods,
        "model": "moving-average-placeholder-v1"
    }
