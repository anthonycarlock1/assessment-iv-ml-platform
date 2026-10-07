# Starts with the project’s Python runtime.
FROM python:3.11-slim
# Runs application commands from /app.
WORKDIR /app
# Copies the requirements file, then pip installs its libraries.
COPY apps/gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Includes the shared service implementation.
COPY apps ./apps
# Documents the port served by this image.
EXPOSE 8000
# Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same
# shared app implementation.
CMD ["uvicorn", "apps.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
