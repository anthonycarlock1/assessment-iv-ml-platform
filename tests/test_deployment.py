# Brings in the libraries, shared code, and test or runtime settings needed below.
import os
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]

# Renders manifests without AWS, then checks namespaces, selectors, images, ConfigMaps,
# ServiceAccounts, probes, budgets, versions, and ingress routes.
def test_rendered_deployment_chain():
    result = subprocess.run([sys.executable, 'scripts/render_manifests.py'], cwd=ROOT,
        env={**os.environ, 'AWS_ACCOUNT_ID': '123456789012', 'IMAGE_TAG': 'test-release', 'AWS_REGION': 'us-east-1', 'ECR_PREFIX': 'anthony-assessment4', 'NAMESPACE': 'fraud-team'},
        capture_output=True, text=True, check=True)
    docs = [doc for doc in yaml.safe_load_all(result.stdout) if doc]
    deployments = {doc['metadata']['name']: doc for doc in docs if doc['kind'] == 'Deployment'}
    services = {doc['metadata']['name']: doc for doc in docs if doc['kind'] == 'Service'}
    assert len(deployments) == 5
    for name, deployment in deployments.items():
        template = deployment['spec']['template']
        assert services[name]['spec']['selector'] == template['metadata']['labels'] or all(
            template['metadata']['labels'][key] == value for key, value in services[name]['spec']['selector'].items())
        service = name.removesuffix('-service')
        namespace = f'{service}-team' if service in ('fraud','forecasting','recommendations') else 'platform-team'
        assert deployment['metadata']['namespace'] == services[name]['metadata']['namespace'] == namespace
        assert deployment['spec']['selector']['matchLabels'].items() <= template['metadata']['labels'].items()
        container = template['spec']['containers'][0]
        for kind in ('ResourceQuota','LimitRange'):
            assert any(doc['kind'] == kind and doc['metadata']['namespace'] == namespace for doc in docs)
        for probe in ('startupProbe','livenessProbe','readinessProbe'):
            assert container[probe]['timeoutSeconds'] > 0
        assert container['startupProbe']['failureThreshold'] * container['startupProbe']['periodSeconds'] >= 150
        assert container['livenessProbe']['httpGet']['path'] == '/health'
        assert container['readinessProbe']['httpGet']['path'] == '/ready'
        assert set(container['resources']['requests']) == set(container['resources']['limits']) == {'cpu','memory'}
        for entry in container.get('envFrom', []):
            assert any(doc['kind'] == 'ConfigMap' and doc['metadata']['namespace'] == namespace and doc['metadata']['name'] == entry['configMapRef']['name'] for doc in docs)
        if service in ('fraud','forecasting','recommendations'):
            assert any(doc['kind'] == 'ServiceAccount' and doc['metadata']['namespace'] == namespace and doc['metadata']['name'] == template['spec']['serviceAccountName'] for doc in docs)
        image = template['spec']['containers'][0]['image']
        assert image.startswith('123456789012.dkr.ecr.us-east-1.amazonaws.com/')
        assert image.endswith('test-release')
        assert 'secretRef' not in str(template)
    ingress = next(doc for doc in docs if doc['metadata']['name'] == 'assessment4-ingress')
    path = ingress['spec']['rules'][0]['http']['paths'][0]
    assert path['path'] == '/api(/|$)(.*)'
    assert path['backend']['service']['name'] == 'gateway-service'
    assert ingress['metadata']['annotations']['nginx.ingress.kubernetes.io/rewrite-target'] == '/$2'
    frontend = next(doc for doc in docs if doc['metadata']['name'] == 'assessment4-frontend')
    assert frontend['spec']['rules'][0]['http']['paths'][0]['backend']['service']['name'] == 'frontend-service'

    assert all(doc['data']['SERVICE_VERSION'] == 'test-release' for doc in docs if doc['kind'] == 'ConfigMap')
    gateway_config = next(doc for doc in docs if doc['kind'] == 'ConfigMap' and doc['metadata']['name'] == 'gateway-config')
    for service in ('fraud','forecasting','recommendations'):
        assert gateway_config['data'][f'{service.upper()}_SERVICE_URL'] == f'http://{service}-service.{service}-team.svc.cluster.local'
    assert {doc['metadata']['name'] for doc in docs if doc['kind'] == 'Namespace'} == {'fraud-team','forecasting-team','recommendations-team','platform-team'}
    assert ingress['metadata']['namespace'] == frontend['metadata']['namespace'] == 'platform-team'
