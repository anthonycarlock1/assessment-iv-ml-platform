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
COPY ml/serving ./ml/serving
COPY data/raw/recommendations_data.csv ./data/raw/recommendations_data.csv
RUN chmod +x /app/ml/serving/entrypoint.sh
# Defaults to local artifact execution inside the SageMaker container.
ENV MODEL_PROVIDER=local
# Documents the port served by this image.
EXPOSE 8080
# Launches the script that accepts SageMaker’s serve argument.
ENTRYPOINT ["/app/ml/serving/entrypoint.sh"]
CMD ["serve"]
