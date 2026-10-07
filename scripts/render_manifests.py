# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Render deployment images before applying manifests; no AWS changes."""
import os
from pathlib import Path
import yaml

root = Path(__file__).resolve().parents[1]
# Requires an account and image tag and reads region/repository prefix settings.
account = os.environ['AWS_ACCOUNT_ID']
tag = os.environ['IMAGE_TAG']
region = os.getenv('AWS_REGION', 'us-east-1')
prefix = os.getenv('ECR_PREFIX', 'anthony-assessment4')
# Reads namespaces, policies, ConfigMaps, ServiceAccounts, Deployments, Services, and ingress.
for folder in ('namespaces', 'policies', 'configmaps', 'serviceaccounts', 'deployments', 'services', 'ingress'):
    for path in sorted((root / 'k8s' / folder).glob('*.yaml')):
        for doc in yaml.safe_load_all(path.read_text()):
            # Marks the configuration with the selected release tag.
            if doc['kind'] == 'ConfigMap':
                doc['data']['SERVICE_VERSION'] = tag
            # Uses each model’s ECR repository, sharing the fraud repository for gateway/frontend
            # tags.
            if doc['kind'] == 'Deployment':
                service = doc['metadata']['name'].removesuffix('-service')
                repo = service if service not in ('gateway', 'frontend') else 'fraud'
                image_tag = tag if service not in ('gateway', 'frontend') else f'{service}-{tag}'
                doc['spec']['template']['spec']['containers'][0]['image'] = f'{account}.dkr.ecr.{region}.amazonaws.com/{prefix}-{repo}:{image_tag}'
            # Prints YAML documents for validation and deployment.
            print(yaml.safe_dump(doc, sort_keys=False), end='---\n')
