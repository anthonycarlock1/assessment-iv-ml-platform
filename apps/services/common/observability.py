# Brings in the libraries, shared code, and test or runtime settings needed below.
import os
import json
import logging
import time
import uuid
from fastapi import Request

logger = logging.getLogger('assessment')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.propagate = False

# Installs shared middleware that adds a request ID and writes one JSON record for each completed
# HTTP request.
def instrument(app, service):
    @app.middleware('http')
    # Validates or generates the request ID, measures duration, adds the ID to the response, and
    # logs service/team/path/status/duration.
    async def context(request: Request, call_next):
        request_id = request.headers.get('x-request-id', '')
        if not request_id or len(request_id) > 64 or not request_id.replace('-', '').isalnum():
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        response.headers['x-request-id'] = request_id
        logger.info(json.dumps({'service': service, 'team': os.getenv('TEAM_NAME', 'fraud-team'), 'request_id': request_id,
            'method': request.method, 'path': request.url.path, 'status': response.status_code,
            'duration_ms': round((time.perf_counter() - start) * 1000, 2)}))
        return response
