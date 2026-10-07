# Starts with the project’s Python runtime.
FROM python:3.11-slim
# Runs application commands from /app.
WORKDIR /app
# Copies the requirements file, then pip installs its libraries.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Includes the shared service implementation.
COPY apps ./apps
# Includes trained models and the recommendation catalog for real artifact execution where needed.
COPY ml/models ./ml/models
COPY data/raw/recommendations_data.csv ./data/raw/recommendations_data.csv
# Documents the port served by this image.
EXPOSE 8000
# Starts Uvicorn with this component’s FastAPI application. The services/ copy uses the same
# shared app implementation.
CMD ["uvicorn", "apps.services.forecasting.main:app", "--host", "0.0.0.0", "--port", "8000"]
