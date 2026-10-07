"""Compatibility entry point; build from the repository root."""
# Re-exports the matching app from apps/services; it does not implement another prediction path.
from apps.services.fraud.main import app
