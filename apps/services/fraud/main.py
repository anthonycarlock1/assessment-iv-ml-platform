# Uses the shared HTTP application factory.
from apps.services.common.api import create_app
# Selects this service’s request and response models.
from apps.services.common.schemas import Transaction, FraudResponse

# Builds this service with common metadata, health, readiness, logging, validation, and prediction
# behavior.
app = create_app("fraud", Transaction, FraudResponse)
