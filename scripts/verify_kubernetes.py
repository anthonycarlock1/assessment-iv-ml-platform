# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Check live workload state, service endpoints and namespace admission policies."""
import datetime
import json
import subprocess

NAMESPACES = {'fraud':'fraud-team','forecasting':'forecasting-team','recommendations':'recommendations-team','gateway':'platform-team','frontend':'platform-team'}

# Runs a Kubernetes command, optionally sending a JSON manifest; raises an error when an expected-
# success command fails.
def kubectl(*args, document=None, success=True):
    result = subprocess.run(['kubectl', *args], input=json.dumps(document) if document else None, capture_output=True, text=True)
    if success and result.returncode:
        raise RuntimeError(result.stderr)
    return result

# Reads one live Kubernetes object as JSON.
def get(namespace, kind, name):
    return json.loads(kubectl('-n',namespace,'get',kind,name,'-o','json').stdout)

# Checks desired/ready replicas, pod state, matching selectors, ready endpoint addresses, and
# probes; uses server dry runs to prove defaults and rejection of oversized/over-budget pods. The
# test pods are never created.
def main():
    rows=[]
    for service, namespace in NAMESPACES.items():
        name=f'{service}-service'
        deployment=get(namespace,'deployment',name)
        desired=deployment['spec']['replicas']
        assert deployment['status']['observedGeneration'] == deployment['metadata']['generation']
        assert deployment['status'].get('readyReplicas',0) == desired
        assert deployment['status'].get('updatedReplicas',0) == desired
        pod_list=json.loads(kubectl('-n',namespace,'get','pods','-l',f'app={name}','-o','json').stdout)['items']
        pods=[pod for pod in pod_list if not pod['metadata'].get('deletionTimestamp')]
        assert len(pods) == desired
        assert all(pod['status']['phase']=='Running' and all(c['ready'] for c in pod['status']['containerStatuses']) for pod in pods)
        selector=get(namespace,'service',name)['spec']['selector']
        assert all(all(pod['metadata']['labels'][key]==value for key,value in selector.items()) for pod in pods)
        slices=json.loads(kubectl('-n',namespace,'get','endpointslices','-l',f'kubernetes.io/service-name={name}','-o','json').stdout)['items']
        addresses=[address for item in slices for endpoint in item['endpoints'] if endpoint['conditions'].get('ready') for address in endpoint['addresses']]
        assert len(addresses) == desired
        container=deployment['spec']['template']['spec']['containers'][0]
        assert container['startupProbe']['httpGet']['path'] == container['livenessProbe']['httpGet']['path'] == '/health'
        assert container['readinessProbe']['httpGet']['path'] == '/ready'
        rows.append({'service':service,'namespace':namespace,'ready_replicas':desired,'ready_endpoints':addresses,'restarts':sum(c['restartCount'] for p in pods for c in p['status']['containerStatuses']),'probes':{p:container[p] for p in ['startupProbe','livenessProbe','readinessProbe']}})
    admission=[]
    for namespace in sorted(set(NAMESPACES.values())):
        quota=get(namespace,'resourcequota','workload-budget')
        limits=get(namespace,'limitrange','container-defaults')
        base={'apiVersion':'v1','kind':'Pod','metadata':{'name':'assessment-admission-check','namespace':namespace},'spec':{'containers':[{'name':'check','image':'registry.k8s.io/pause:3.10'}]}}
        result=json.loads(kubectl('create','--dry-run=server','-f','-','-o','json',document=base).stdout)
        assert result['spec']['containers'][0]['resources']['requests'] == limits['spec']['limits'][0]['defaultRequest']
        base['spec']['containers'][0]['resources']={'requests':{'cpu':'2','memory':'128Mi'},'limits':{'cpu':'2','memory':'512Mi'}}
        rejected=kubectl('create','--dry-run=server','-f','-',document=base,success=False)
        assert rejected.returncode and 'maximum cpu' in rejected.stderr, rejected.stderr
        base['spec']['containers']=[{'name':f'check-{i}','image':'registry.k8s.io/pause:3.10','resources':{'requests':{'cpu':'100m','memory':'128Mi'},'limits':{'cpu':'1','memory':'1Gi'}}} for i in range(7)]
        rejected=kubectl('create','--dry-run=server','-f','-',document=base,success=False)
        assert rejected.returncode and 'exceeded quota' in rejected.stderr, rejected.stderr
        admission.append({'namespace':namespace,'quota':quota['spec']['hard'],'default_resources_verified':True,'oversized_container_rejected':True,'over_budget_pod_rejected':True})
    print(json.dumps({'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'workloads':rows,'admission':admission},indent=2))

if __name__=='__main__': main()
