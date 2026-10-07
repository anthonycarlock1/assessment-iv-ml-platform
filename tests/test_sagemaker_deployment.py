# Brings in the libraries, shared code, and test or runtime settings needed below.
from scripts.deploy_sagemaker import endpoint_config, role_policy, workload_trust, ENDPOINTS, NAMESPACES

# Checks the endpoint configuration uses on-demand serverless settings rather than fixed
# instances.
def test_serverless_has_no_always_on_instances():
    config = endpoint_config('test-model')
    variant = config['ProductionVariants'][0]
    assert variant['ServerlessConfig'] == {'MemorySizeInMB':2048,'MaxConcurrency':2}
    assert 'InstanceType' not in variant
    assert 'InitialInstanceCount' not in variant

# Checks each role can invoke only its endpoint and trusts only the intended
# cluster/namespace/service account.
def test_workload_permissions_are_service_specific():
    for service in ENDPOINTS:
        policy = role_policy(service)['Statement']
        assert len(policy) == 1
        assert policy[0]['Action'] == 'sagemaker:InvokeEndpoint'
        assert policy[0]['Resource'].endswith('/' + ENDPOINTS[service])
        trust = workload_trust(service)['Statement'][0]
        assert trust['Condition']['StringEquals']['aws:RequestTag/kubernetes-namespace'] == NAMESPACES[service]
        assert trust['Condition']['StringEquals']['aws:RequestTag/kubernetes-service-account'] == f'{service}-sagemaker'
        assert trust['Condition']['StringEquals']['aws:RequestTag/eks-cluster-name'] == 'anthony-assessment4-eks'

# Checks a failed endpoint invocation prevents Kubernetes configuration from being written.
def test_bind_does_not_change_files_before_verified(monkeypatch, tmp_path):
    import scripts.deploy_sagemaker as deploy
    monkeypatch.setattr(deploy, 'ROOT', tmp_path)
    def fail():
        raise RuntimeError('Endpoint invocation failed')
    monkeypatch.setattr(deploy, 'verify', fail)
    import pytest
    with pytest.raises(RuntimeError): deploy.bind()
    assert not (tmp_path / 'k8s').exists()

# Checks verified endpoints are bound to the correct configuration and workload identity.
def test_bind_assigns_correct_service_accounts_and_endpoints(monkeypatch, tmp_path):
    import scripts.deploy_sagemaker as deploy
    import yaml
    for service in ENDPOINTS:
        config = tmp_path / f'k8s/configmaps/{service}-config.yaml'
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(yaml.safe_dump({'data':{'SERVICE_NAME':service,'MODEL_PROVIDER':'local'}}))
        manifest = tmp_path / f'k8s/deployments/{service}.yaml'
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(yaml.safe_dump({'spec':{'template':{'spec':{'containers':[{'name':service}]}}}}))
    verified=[]
    monkeypatch.setattr(deploy, 'ROOT', tmp_path)
    monkeypatch.setattr(deploy, 'verify', lambda:verified.append(True))
    deploy.bind()
    assert verified == [True]
    for service, endpoint in ENDPOINTS.items():
        config = yaml.safe_load((tmp_path / f'k8s/configmaps/{service}-config.yaml').read_text())['data']
        assert config['MODEL_PROVIDER'] == 'sagemaker'
        assert config[f'{service.upper()}_SAGEMAKER_ENDPOINT'] == endpoint
        sa = yaml.safe_load((tmp_path / f'k8s/serviceaccounts/{service}.yaml').read_text())
        assert sa['metadata']['namespace'] == NAMESPACES[service]
        manifest = yaml.safe_load((tmp_path / f'k8s/deployments/{service}.yaml').read_text())
        assert manifest['spec']['template']['spec']['serviceAccountName'] == sa['metadata']['name']

# Checks migration uses dedicated roles and refuses an unexpected existing identity association.
def test_identity_migration_keeps_old_roles_and_rejects_wrong_binding(monkeypatch):
    import scripts.deploy_sagemaker as deploy
    import pytest
    calls=[]
    class EKS:
        def list_addons(self, **kwargs): return {'addons':['eks-pod-identity-agent']}
        def list_pod_identity_associations(self, **kwargs):
            calls.append(kwargs)
            return {'associations':[{'associationId':'existing'}]}
        def describe_pod_identity_association(self, **kwargs):
            return {'association':{'roleArn':'arn:aws:iam::388691194728:role/unexpected-role'}}
    class Session:
        def client(self, service): return EKS() if service == 'eks' else object()
    roles=[]
    monkeypatch.setattr(deploy, 'ensure_role', lambda iam,name,trust,policy:roles.append(name))
    with pytest.raises(RuntimeError, match='Unexpected existing Pod Identity association'):
        deploy.configure_identity(Session())
    assert roles == ['anthony-assessment4-fraud-invoke','anthony-assessment4-forecasting-invoke-v2','anthony-assessment4-recommendations-invoke-v2']
    assert calls[0]['namespace'] == 'fraud-team'


def test_hosting_name_preserves_existing_names_and_bounds_long_releases():
    from scripts.deploy_sagemaker import hosting_name
    assert hosting_name('fraud', 'sm-v1') == 'anthony-assessment4-fraud-sm-v1'
    release = 'sm-presentation-20261007T022227Z'
    assert hosting_name('fraud', release) == f'anthony-assessment4-fraud-{release}'
    for service in ('forecasting', 'recommendations'):
        name = hosting_name(service, release)
        assert len(name) <= 63
        assert name.startswith(f'anthony-assessment4-{service}-')
        assert name == hosting_name(service, release)
        assert name != hosting_name(service, release + 'x')
