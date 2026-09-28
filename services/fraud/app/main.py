from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Fraud Detection Service",
    version="1.0.0"
)


class Transaction(BaseModel):
    amount: float
    transaction_count: int
    account_age_days: int


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "fraud-detection"
    }


@app.get("/ready")
def ready():
    return {
        "status": "ready"
    }


@app.post("/predict")
def predict(transaction: Transaction):
    # Temporary local logic.
    # Later this will invoke SageMaker.
    risk_score = 0

    if transaction.amount > 1000:
        risk_score += 1

    if transaction.transaction_count > 20:
        risk_score += 1

    if transaction.account_age_days < 30:
        risk_score += 1

    prediction = "fraud" if risk_score >= 2 else "legitimate"

    return {
        "prediction": prediction,
        "risk_score": risk_score,
        "model": "fraud-local-placeholder-v1"
    }