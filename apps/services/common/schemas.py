# Brings in the libraries, shared code, and test or runtime settings needed below.
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

# Rejects extra fields and non-finite numbers, so requests cannot contain unexpected data, NaN, or
# Infinity.
class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

# Defines the fraud inputs: amount, transaction count, and account age; all must be nonnegative.
class Transaction(Input):
    amount: float = Field(ge=0)
    transaction_count: int = Field(ge=0)
    account_age_days: int = Field(ge=0)

# Requires a history of numbers and a bounded number of future periods.
class ForecastRequest(Input):
    values: list[float] = Field(min_length=1, max_length=1000)
    periods: int = Field(default=3, ge=1, le=100)

# Requires a positive user ID, a category, and a bounded result limit.
class RecommendationRequest(Input):
    user_id: int = Field(ge=1)
    category: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=3, ge=1, le=100)

# Adds the model name and states whether inference came from local execution or SageMaker.
class Output(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    model: str
    provider: Literal['local', 'sagemaker']

# Allows only fraud/legitimate labels and a risk score between zero and one.
class FraudResponse(Output):
    prediction: Literal['fraud', 'legitimate']
    risk_score: float = Field(ge=0, le=1)

# Defines the predicted values and the number of periods.
class ForecastResponse(Output):
    forecast: list[float]
    periods: int = Field(ge=1, le=100)

# Defines one recommended item, its category, and its score.
class Recommendation(BaseModel):
    item_id: str
    category: str
    score: float = Field(ge=0, le=1)

# Groups ranked items under the requested user ID.
class RecommendationResponse(Output):
    user_id: int
    recommendations: list[Recommendation]
