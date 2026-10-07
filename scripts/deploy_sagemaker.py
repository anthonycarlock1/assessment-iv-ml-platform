# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Provision only this project's serverless hosting resources; never delete resources.

plan is offline. provision creates dedicated IAM roles and endpoints. bind writes
Kubernetes configuration only after every endpoint passes a real invocation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import boto3
from botocore.exceptions import ClientError
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SERVICES = ('fraud', 'forecasting', 'recommendations')
PREFIX = 'anthony-assessment4'
REGION = 'us-east-1'
CLUSTER = 'anthony-assessment4-eks'
ACCOUNT = '388691194728'
NAMESPACES = {s: f'{s}-team' for s in SERVICES}
WORKLOAD_ROLES = {s: f'{PREFIX}-{s}-invoke' + ('' if s == 'fraud' else '-v2') for s in SERVICES}
ENDPOINTS = {s: f'{PREFIX}-{s}-sagemaker' for s in SERVICES}
SAMPLES = {
    'fraud': {'amount':1800, 'transaction_count':35, 'account_age_days':12},
    'forecasting': {'values':[10,20,30], 'periods':2},
    'recommendations': {'user_id':12, 'category':'electronics', 'limit':2},
}

# Labels created resources with the project and Anthony’s ownership.
def tags():
    return [{'Key': 'Project', 'Value': PREFIX}, {'Key': 'Owner', 'Value': 'anthony'}]

# Builds endpoint-only invocation permissions for an adapter, or image-pull/log-writing
# permissions for hosting.
def role_policy(service=None):
    if service:
        return {'Version':'2012-10-17', 'Statement':[{'Effect':'Allow', 'Action':'sagemaker:InvokeEndpoint',
            'Resource':f'arn:aws:sagemaker:{REGION}:{ACCOUNT}:endpoint/{ENDPOINTS[service]}'}]}
    return {'Version':'2012-10-17', 'Statement':[
        {'Effect':'Allow','Action':'ecr:GetAuthorizationToken','Resource':'*'},
        {'Effect':'Allow','Action':['ecr:BatchGetImage','ecr:GetDownloadUrlForLayer','ecr:BatchCheckLayerAvailability'],
         'Resource':f'arn:aws:ecr:{REGION}:{ACCOUNT}:repository/{PREFIX}-fraud'},
        {'Effect':'Allow','Action':['logs:CreateLogGroup','logs:CreateLogStream','logs:PutLogEvents','logs:DescribeLogStreams'],
         'Resource':f'arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/sagemaker/Endpoints/{PREFIX}-*:*'}]}

# Allows SageMaker in the intended AWS account to assume the execution role.
def hosting_trust():
    return {'Version':'2012-10-17','Statement':[{'Effect':'Allow','Principal':{'Service':'sagemaker.amazonaws.com'},
        'Action':'sts:AssumeRole', 'Condition':{'StringEquals':{'aws:SourceAccount':ACCOUNT},
        'ArnLike':{'aws:SourceArn':f'arn:aws:sagemaker:{REGION}:{ACCOUNT}:*'}}}]}

# Allows EKS Pod Identity to assume a role only for the selected cluster, namespace, and service
# account.
def workload_trust(service):
    return {'Version':'2012-10-17','Statement':[{'Effect':'Allow',
        'Principal':{'Service':'pods.eks.amazonaws.com'},
        'Action':['sts:AssumeRole','sts:TagSession'],'Condition':{'StringEquals':{
            'aws:RequestTag/eks-cluster-name':CLUSTER,
            'aws:RequestTag/kubernetes-namespace':NAMESPACES[service],
            'aws:RequestTag/kubernetes-service-account':f'{service}-sagemaker'}}}]}

# Reuses an expected owned role or creates it, attaches its policy, and refuses an unexpected
# role/trust definition.
def ensure_role(iam, name, trust, policy):
    try:
        role = iam.get_role(RoleName=name)['Role']
        existing_tags = {t['Key']:t['Value'] for t in role.get('Tags', [])}
        if existing_tags.get('Project') != PREFIX or role['AssumeRolePolicyDocument'] != trust:
            raise RuntimeError(f'Refusing to modify an unexpected role: {name}')
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'NoSuchEntity': raise
        role = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust), Tags=tags())['Role']
    iam.put_role_policy(RoleName=name, PolicyName='assessment4-inference-only', PolicyDocument=json.dumps(policy))
    print(f'Role ready: {name}', flush=True)
    return role['Arn']

# Builds the 2 GB, maximum-concurrency-two serverless endpoint configuration.
def endpoint_config(name):
    return {'EndpointConfigName':name,'ProductionVariants':[{'VariantName':'AllTraffic', 'ModelName':name,
        'ServerlessConfig':{'MemorySizeInMB':2048,'MaxConcurrency':2}}], 'Tags':tags()}

# Ensures the Pod Identity agent, dedicated invocation roles, and matching workload associations
# exist.
def configure_identity(session):
    iam = session.client('iam')
    eks = session.client('eks')
    for service in SERVICES:
        ensure_role(iam, WORKLOAD_ROLES[service], workload_trust(service), role_policy(service))
    if 'eks-pod-identity-agent' not in eks.list_addons(clusterName=CLUSTER)['addons']:
        eks.create_addon(clusterName=CLUSTER, addonName='eks-pod-identity-agent', tags={'Project':PREFIX,'Owner':'anthony'})
    for service in SERVICES:
        associations = eks.list_pod_identity_associations(clusterName=CLUSTER, namespace=NAMESPACES[service], serviceAccount=f'{service}-sagemaker')['associations']
        if not associations:
            eks.create_pod_identity_association(clusterName=CLUSTER, namespace=NAMESPACES[service], serviceAccount=f'{service}-sagemaker',
                roleArn=f'arn:aws:iam::{ACCOUNT}:role/{WORKLOAD_ROLES[service]}', tags={'Project':PREFIX,'Owner':'anthony'})
        else:
            existing = eks.describe_pod_identity_association(clusterName=CLUSTER,associationId=associations[0]['associationId'])['association']
            if existing['roleArn'] != f'arn:aws:iam::{ACCOUNT}:role/{WORKLOAD_ROLES[service]}':
                raise RuntimeError('Unexpected existing Pod Identity association')

# Checks the AWS account before configuring workload identity, without creating SageMaker
# endpoints.
def identity():
    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise RuntimeError('Unexpected AWS account')
    configure_identity(session)

# Checks the account and immutable project image, then creates missing
# models/configurations/endpoints and refuses conflicting existing releases.
def hosting_name(service, release):
    """Keep short names unchanged; shorten long names with a stable collision suffix."""
    name = f'{PREFIX}-{service}-{release}'
    if len(name) > 63:
        name = name[:54].rstrip('-') + '-' + hashlib.sha256(name.encode()).hexdigest()[:8]
    return name


def provision(image, release):
    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise RuntimeError('Unexpected AWS account')
    if not image.startswith(f'{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com/{PREFIX}-fraud@sha256:'):
        raise RuntimeError('Use an immutable digest from the existing project fraud repository')
    iam = session.client('iam')
    execution_role = ensure_role(iam, f'{PREFIX}-sagemaker-execution', hosting_trust(), role_policy())
    configure_identity(session)
    sm = session.client('sagemaker')
    for service in SERVICES:
        name = hosting_name(service, release)
        # Check existence explicitly; do not catch validation failures from creation.
        existing = sm.list_models(NameContains=name)['Models']
        if not any(m['ModelName'] == name for m in existing):
            sm.create_model(ModelName=name, ExecutionRoleArn=execution_role, Tags=tags(),
                PrimaryContainer={'Image':image,'Environment':{'SERVICE_NAME':service,'MODEL_PROVIDER':'local'}})
        else:
            model = sm.describe_model(ModelName=name)
            if model['PrimaryContainer']['Image'] != image:
                raise RuntimeError(f'Model release collision: {name}; use a new release')
        configs = sm.list_endpoint_configs(NameContains=name)['EndpointConfigs']
        if not any(c['EndpointConfigName'] == name for c in configs):
            sm.create_endpoint_config(**endpoint_config(name))
        endpoints = sm.list_endpoints(NameContains=ENDPOINTS[service])['Endpoints']
        if not any(e['EndpointName'] == ENDPOINTS[service] for e in endpoints):
            sm.create_endpoint(EndpointName=ENDPOINTS[service], EndpointConfigName=name, Tags=tags())
        else:
            endpoint = sm.describe_endpoint(EndpointName=ENDPOINTS[service])
            if endpoint['EndpointConfigName'] != name:
                raise RuntimeError(f'Existing endpoint uses another release: {ENDPOINTS[service]}; review before updating')
        print(f'Endpoint requested: {ENDPOINTS[service]}', flush=True)
    print('Run status until all endpoints are InService, then verify and bind.')

# Reads each endpoint’s AWS deployment status and any failure reason.
def status():
    sm = boto3.client('sagemaker',region_name=REGION)
    for name in ENDPOINTS.values():
        try:
            result = sm.describe_endpoint(EndpointName=name)
            print(json.dumps({'endpoint':name,'status':result['EndpointStatus'], 'failure':result.get('FailureReason')}))
        except ClientError as exc:
            print(json.dumps({'endpoint':name,'error':exc.response['Error']['Code']}))

# Invokes every real endpoint and validates meaningful fraud, forecast, and recommendation output.
def verify():
    from botocore.config import Config
    from apps.services.common.schemas import FraudResponse, ForecastResponse, RecommendationResponse
    contracts = {'fraud':FraudResponse,'forecasting':ForecastResponse,'recommendations':RecommendationResponse}
    sm = boto3.client('sagemaker',region_name=REGION)
    runtime = boto3.client('sagemaker-runtime',region_name=REGION,config=Config(connect_timeout=3,read_timeout=70))
    for service, name in ENDPOINTS.items():
        if sm.describe_endpoint(EndpointName=name)['EndpointStatus'] != 'InService':
            raise RuntimeError(f'{name} is not InService')
        response = runtime.invoke_endpoint(EndpointName=name,ContentType='application/json',Body=json.dumps(SAMPLES[service]))
        stream = response['Body']
        try: result = json.loads(stream.read())
        finally: stream.close()
        validated = contracts[service].model_validate({**result,'provider':'sagemaker'})
        if service == 'fraud': assert validated.prediction == 'fraud' and validated.risk_score > 0.5
        if service == 'forecasting': assert len(validated.forecast) == validated.periods == 2
        if service == 'recommendations': assert validated.user_id == 12 and len(validated.recommendations) == 2
        print(json.dumps({'endpoint':name,'result':validated.model_dump()}), flush=True)

# Verifies endpoints first, then writes environment configuration and Kubernetes ServiceAccounts
# for the adapters.
def bind():
    verify()
    account_dir = ROOT / 'k8s/serviceaccounts'
    account_dir.mkdir(exist_ok=True)
    for service in SERVICES:
        path = ROOT / f'k8s/configmaps/{service}-config.yaml'
        doc = yaml.safe_load(path.read_text())
        doc.setdefault('metadata', {})['namespace'] = NAMESPACES[service]
        doc['data'].update({'MODEL_PROVIDER':'sagemaker','AWS_REGION':REGION,
            f'{service.upper()}_SAGEMAKER_ENDPOINT':ENDPOINTS[service]})
        path.write_text(yaml.safe_dump(doc,sort_keys=False))
        path = ROOT / f'k8s/deployments/{service}.yaml'
        doc = yaml.safe_load(path.read_text())
        doc.setdefault('metadata', {})['namespace'] = NAMESPACES[service]
        doc['spec']['template']['spec']['serviceAccountName'] = f'{service}-sagemaker'
        path.write_text(yaml.safe_dump(doc,sort_keys=False))
        sa = {'apiVersion':'v1','kind':'ServiceAccount','metadata':{'name':f'{service}-sagemaker','namespace':NAMESPACES[service],
            'labels':{'app.kubernetes.io/part-of':PREFIX}}}
        (account_dir / f'{service}.yaml').write_text(yaml.safe_dump(sa,sort_keys=False))
    print('Kubernetes files configured; build/push application images and run deploy.sh.')

# Selects the requested command: offline plan, identity setup, provision, status, verify, or bind.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['plan','provision','status','verify','bind','identity'])
    parser.add_argument('--image')
    parser.add_argument('--release',default='sm-v1')
    args = parser.parse_args()
    if args.action == 'plan':
        print(json.dumps({'account':ACCOUNT,'region':REGION,'endpoints':ENDPOINTS,'serverless':{'memory_mb':2048,'max_concurrency':2,'provisioned_concurrency':0},
            'eks_addon':'eks-pod-identity-agent','execution_role':f'{PREFIX}-sagemaker-execution','workload_roles':list(WORKLOAD_ROLES.values()),'workload_namespaces':NAMESPACES,
            'existing_resources_preserved':['EKS','node groups','ECR','other students endpoints'],
            'execution_policy':role_policy(),'invoke_policies':{s:role_policy(s) for s in SERVICES}},indent=2))
    elif args.action == 'provision':
        if not args.image: parser.error('--image is required')
        provision(args.image,args.release)
    else: globals()[args.action]()

# Runs the command parser when invoked as a script.
if __name__ == '__main__':
    main()
