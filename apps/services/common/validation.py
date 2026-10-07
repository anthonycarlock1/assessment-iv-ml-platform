# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Safe, JSON-serializable request errors shared by APIs and gateway."""
import math
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# Registers a 422 error handler that returns field locations and explanations without echoing
# unsafe raw input.
def install_validation_handler(app):
    @app.exception_handler(RequestValidationError)
    # Turns Pydantic validation failures into JSON-safe field error details.
    async def invalid_request(request, exc):
        # Pydantic's input/context may contain NaN, exceptions, or sensitive data.
        # Keep field locations and explanations without echoing the input body.
        details = [{key: error[key] for key in ('loc', 'msg', 'type')} for error in exc.errors()]
        return JSONResponse(status_code=422, content={'detail': details})


# Walks nested dictionaries/lists and rejects NaN or Infinity before forwarding a request.
def require_finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise HTTPException(422, 'JSON numbers must be finite')
    if isinstance(value, dict):
        for child in value.values():
            require_finite_json(child)
    elif isinstance(value, list):
        for child in value:
            require_finite_json(child)
