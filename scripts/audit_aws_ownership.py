# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Read-only ownership inventory for resources created by this deployment."""
import json
import boto3
from deploy_sagemaker import ACCOUNT, REGION, PREFIX, SERVICES, ENDPOINTS, CLUSTER, NAMESPACES, WORKLOAD_ROLES

session=boto3.Session(region_name=REGION)
sm=session.client('sagemaker')
iam=session.client('iam')
eks=session.client('eks')
rows=[]
# Normalizes AWS tags into an ownership-inventory row.
def record(kind,name,arn,tags):
    values={item['Key']:item['Value'] for item in tags} if isinstance(tags,list) else tags
    rows.append({'type':kind,'name':name,'arn':arn,'owner':values.get('Owner'),'project':values.get('Project')})

# Reads model/endpoint/configuration tags for each service.
for service in SERVICES:
    endpoint=sm.describe_endpoint(EndpointName=ENDPOINTS[service])
    config=sm.describe_endpoint_config(EndpointConfigName=endpoint['EndpointConfigName'])
    model=sm.describe_model(ModelName=config['ProductionVariants'][0]['ModelName'])
    for kind,obj,name_key,arn_key in [('endpoint',endpoint,'EndpointName','EndpointArn'),('endpoint-config',config,'EndpointConfigName','EndpointConfigArn'),('model',model,'ModelName','ModelArn')]:
        record(kind,obj[name_key],obj[arn_key],sm.list_tags(ResourceArn=obj[arn_key])['Tags'])
# Includes active roles and older roles retained for rollback.
for name in list(dict.fromkeys([f'{PREFIX}-sagemaker-execution']+list(WORKLOAD_ROLES.values())+[f'{PREFIX}-{s}-invoke' for s in SERVICES])):
    role=iam.get_role(RoleName=name)['Role']
    record('role',name,role['Arn'],role.get('Tags',[]))
# Reads add-on and Pod Identity association tags.
addon=eks.describe_addon(clusterName=CLUSTER,addonName='eks-pod-identity-agent')['addon']
record('eks-addon',addon['addonName'],addon['addonArn'],addon.get('tags',{}))
for service in SERVICES:
    for namespace in sorted({NAMESPACES[service], 'fraud-team'}):
        associations=eks.list_pod_identity_associations(clusterName=CLUSTER,namespace=namespace,serviceAccount=f'{service}-sagemaker')['associations']
        for association in associations:
            details=eks.describe_pod_identity_association(clusterName=CLUSTER,associationId=association['associationId'])['association']
            record('pod-identity',f"{namespace}/{details['serviceAccount']}",details['associationArn'],details.get('tags',{}))
print(json.dumps(rows,indent=2))
# Fails if any tracked resource is missing Anthony’s owner tag.
if any(row['owner'] != 'anthony' for row in rows):
    raise SystemExit('An owned resource is missing the anthony owner tag')
