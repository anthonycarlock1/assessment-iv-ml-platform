# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Verify operational metadata and probes through the deployed frontend proxy."""
import subprocess
# Defines a small Python program to execute inside the deployed gateway pod; these checks use real
# Service DNS addresses.
CODE = '''import datetime,json,urllib.request
base='http://frontend-service.platform-team.svc.cluster.local/api'
rows=[]
for service in ['fraud','forecasting','recommendations']:
    metadata=json.load(urllib.request.urlopen(base+'/'+service+'/metadata',timeout=10))
    assert metadata['service']==service
    assert metadata['team']==service+'-team'
    assert metadata['model']==service+'-model-v1'
    assert metadata['model_version']=='v1'
    assert metadata['service_version']
    assert metadata['provider']=='sagemaker'
    assert metadata['endpoint']=='anthony-assessment4-'+service+'-sagemaker'
    assert metadata['region']=='us-east-1'
    probes={}
    for path,expected in [('health','healthy'),('ready','ready')]:
        body=json.load(urllib.request.urlopen(base+'/'+service+'/'+path,timeout=10))
        assert body['service']==service and body['status']==expected
        probes[path]=body
    rows.append({'metadata':metadata,'probes':probes})
assert len({row['metadata']['service_version'] for row in rows})==1
print(json.dumps({'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'services':rows},indent=2))
'''
if __name__=='__main__':
    # Uses kubectl exec to run the check in platform-team, and fails the script if verification
    # fails.
    subprocess.run(['kubectl','-n','platform-team','exec','deployment/gateway-service','--','python','-c',CODE],check=True)
