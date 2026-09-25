from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(
    title="Recommendations Service",
    version="1.0.0"
)


class RecommendationRequest(BaseModel):
    user_id: int
    category: str
    limit: int = 3


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "recommendations"
    }


@app.get("/ready")
def ready():
    return {
        "status": "ready"
    }


@app.post("/predict")
def predict(request: RecommendationRequest):

    # Local placeholder until SageMaker endpoint is connected.
    recommendations = [
        {
            "item_id": "item-101",
            "category": request.category,
            "score": 0.94
        },
        {
            "item_id": "item-205",
            "category": request.category,
            "score": 0.87
        },
        {
            "item_id": "item-309",
            "category": request.category,
            "score": 0.81
        }
    ]

    return {
        "user_id": request.user_id,
        "recommendations": recommendations[:request.limit],
        "model": "recommendations-local-placeholder-v1"
    }