# Assessment IV ML Platform Plan

## Goal

Build a production-ready ML platform that contains:

- a Kubernetes-backed deployment model
- multiple microservices for fraud detection, forecasting, and recommendations
- AWS infrastructure managed via Terraform
- CI/CD automation for image builds and deploys
- monitoring, security, and operational documentation

## Project Segments

### 1. Core Infrastructure

Focus: create the base cloud platform.

Deliverables:
- VPC and subnets
- Security groups
- EKS cluster
- Node groups or Fargate config
- ECR repos
- IAM roles and policies
- Terraform state and environment separation

Files to create or extend:
- terraform/modules/vpc/
- terraform/modules/eks/
- terraform/modules/ecr/
- terraform/modules/iam/
- terraform/environments/dev/
- terraform/environments/staging/
- terraform/environments/prod/

### 2. Kubernetes Platform

Focus: deploy applications in isolated environments.

Deliverables:
- namespaces
- configmaps and secrets
- deployments
- services
- ingress
- autoscaling
- resource limits and quotas
- health checks / readiness probes

Files to create:
- infra/k8s/namespaces/
- infra/k8s/configmaps/
- infra/k8s/secrets/
- infra/k8s/deployments/
- infra/k8s/services/
- infra/k8s/ingress/
- infra/k8s/observability/

### 3. App Services

Focus: containerized ML APIs.

Deliverables:
- fraud detection microservice
- forecasting microservice
- recommendations microservice
- Dockerfiles and dependency files
- tests for endpoints and basic validation

Files to create:
- apps/services/fraud/
- apps/services/forecasting/
- apps/services/recommendations/

### 4. ML and Model Layer

Focus: move from placeholder logic to real model workflows.

Deliverables:
- training pipelines
- scripts for feature prep and model training
- model registry strategy
- inference endpoint integration
- model versioning documentation

Files to create:
- ml/training/
- ml/pipelines/
- ml/models/
- ml/notebooks/

### 5. Dashboard and User Experience

Focus: expose insights and platform status visually.

Deliverables:
- admin dashboard
- health and KPI summary pages
- API-driven metrics viewer
- deployment status panel

Files to create:
- apps/dashboard/frontend/
- apps/dashboard/backend/

### 6. CI/CD and Automation

Focus: make deployments repeatable.

Deliverables:
- GitHub Actions workflow
- image build stage
- ECR push
- kubectl apply or helm deploy
- lint/test gates

Files to create:
- .github/workflows/ci-cd.yml
- scripts/build.sh
- scripts/deploy.sh
- scripts/bootstrap.sh

### 7. Observability and Reliability

Focus: production operations.

Deliverables:
- Prometheus / Grafana configuration
- alert rules
- log aggregation setup
- dashboards
- runbooks and incident response docs

Files to create:
- monitoring/dashboards/
- monitoring/alerts/
- docs/runbooks/

### 8. Security and Governance

Focus: production safety.

Deliverables:
- secret management via AWS Secrets Manager or Kubernetes secrets
- IAM least privilege
- network policies
- security docs
- secure config patterns

Files to create:
- docs/security/
- infra/k8s/networkpolicies/

## Suggested Delivery Order

1. Infrastructure foundation
2. Kubernetes base platform
3. App service containerization
4. Health and readiness checks
5. CI/CD workflows
6. Real ML model integration
7. Monitoring and alerting
8. Documentation and hardening

## Milestone 1: Foundation Ready

Complete when:
- Terraform provisions base AWS resources
- EKS is connected and accessible
- namespace structure exists
- services can deploy to Kubernetes

## Milestone 2: Services Running

Complete when:
- all three microservices are built and running
- /health and /ready endpoints pass
- service-to-service and ingress paths are verified

## Milestone 3: Production Quality

Complete when:
- model integration is in place
- monitoring and alerts are enabled
- security and secrets are implemented
- deployment automation supports dev/staging/prod

## Recommended Workstream Split

### Workstream A: Infrastructure
- Terraform modules
- AWS base setup
- EKS and IAM

### Workstream B: Platform
- Kubernetes manifests
- ingress
- resource constraints
- observability

### Workstream C: Applications
- service APIs
- request/response schemas
- Dockerization
- testing

### Workstream D: ML
- training pipelines
- model deployment strategy
- feature engineering

### Workstream E: DevOps
- CI/CD
- build and deploy automation
- environment promotion

## Final Outcome

The finished platform should look and behave like a real internal ML product:

- secure and environment-aware
- deployable through IaC
- containerized and scalable
- observable and production-safe
- modular so each service and model can evolve independently
