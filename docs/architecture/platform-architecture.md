# Platform Architecture

## High-Level System Architecture

```mermaid
flowchart TD
    Client[External Client / Dashboard / Internal User]
    Ingress[Ingress / ALB / API Gateway]
    NS1[Namespace: fraud-team]
    NS2[Namespace: analytics-team]

    Fraud[Fraud Detection Service]
    Forecast[Forecasting Service]
    Rec[Recommendations Service]

    EKS[EKS Cluster]
    ECR[ECR Repository]
    IAM[IAM / Roles]
    S3[(S3 for artifacts / data)]
    Model[Model Endpoint / SageMaker / Inference Service]
    Obs[Monitoring / Metrics / Logs]

    Client --> Ingress
    Ingress --> Fraud
    Ingress --> Forecast
    Ingress --> Rec

    Fraud --> EKS
    Forecast --> EKS
    Rec --> EKS

    EKS --> ECR
    EKS --> IAM
    Fraud --> Model
    Forecast --> Model
    Rec --> Model
    Fraud --> S3
    Forecast --> S3
    Rec --> S3
    Fraud --> Obs
    Forecast --> Obs
    Rec --> Obs
```

## Deployment Pattern

```mermaid
flowchart LR
    CI[GitHub Actions] --> Build[Build Container Images]
    Build --> Push[ECR Push]
    Push --> K8s[Kubernetes Deployment]
    K8s --> Deploy[Fraud / Forecasting / Recommendations]
    Deploy --> Health[Readiness and Liveness Checks]
    Health --> Monitor[Prometheus / Grafana / CloudWatch]
```

## Service Interaction Model

```mermaid
sequenceDiagram
    participant User
    participant Ingress
    participant Fraud
    participant Forecast
    participant Recommendation
    participant Model

    User->>Ingress: API request
    Ingress->>Fraud: /predict
    Ingress->>Forecast: /predict
    Ingress->>Recommendation: /predict

    Fraud->>Model: inference request
    Forecast->>Model: inference request
    Recommendation->>Model: inference request

    Model-->>Fraud: prediction result
    Model-->>Forecast: prediction result
    Model-->>Recommendation: prediction result

    Fraud-->>User: risk result
    Forecast-->>User: forecast output
    Recommendation-->>User: recommendations
```

## Infrastructure Layer

This project should eventually include:

- AWS VPC with private/public subnets
- EKS control plane and worker nodes
- container registry in ECR
- Kubernetes namespaces per workload
- IAM policies and service accounts
- S3 and optional database storage for training and serving data
- ingress/load balancing for application access

## Application Layer

The app layer contains:

- fraud detection microservice
- forecasting microservice
- recommendations microservice
- optional dashboard or admin UI

Each service exposes:

- /health
- /ready
- /predict

## ML Layer

The ML layer can be implemented using:

- SageMaker endpoints
- custom model-serving containers
- feature stores and data pipelines
- model training scripts and registry metadata

## Operational Layer

Operational concerns include:

- CI/CD pipelines
- logging and dashboards
- autoscaling
- alerting
- incident response and runbooks
- infrastructure as code with Terraform
