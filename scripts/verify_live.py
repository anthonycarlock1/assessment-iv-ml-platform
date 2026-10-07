# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Verify the deployed frontend HTTP proxy through to real SageMaker results."""
import json
import subprocess

# Defines a small Python program to execute inside the deployed gateway pod; these checks use real
# Service DNS addresses.
CODE = '''import json, re, urllib.request
base='http://frontend-service.platform-team.svc.cluster.local'
page=urllib.request.urlopen(base, timeout=10).read().decode()
assert '<html' in page.lower()
assert '/assets/' in page
assets=[]
for asset in re.findall(r'(?:src|href)="(/assets/[^"]+)"',page):
    response=urllib.request.urlopen(base+asset,timeout=10)
    assert response.status==200 and response.read()
    assert 'text/html' not in response.headers.get('Content-Type','')
    assets.append(asset)
assert assets
assert json.load(urllib.request.urlopen(base+'/api/ready', timeout=30))['status']=='ready'
probes=[]
for path in ['/health','/ready']:
    response=urllib.request.urlopen(base+path,timeout=10)
    assert response.status==200
    probes.append({'path':path,'status':response.status})
for service in ['fraud','forecasting','recommendations']:
    for endpoint,expected in [('health','healthy'),('ready','ready')]:
        path='/api/'+service+'/'+endpoint
        response=urllib.request.urlopen(base+path,timeout=30)
        result=json.load(response)
        assert result['status']==expected, result
        probes.append({'path':path,'status':response.status,'result':result})
results=[]
for service,payload in [('fraud',{'amount':1800,'transaction_count':35,'account_age_days':12}),('forecasting',{'values':[10,20,30],'periods':2}),('recommendations',{'user_id':12,'category':'electronics','limit':2})]:
    request=urllib.request.Request(base+'/api/'+service+'/predict',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    response=urllib.request.urlopen(request,timeout=90)
    result=json.load(response)
    assert result['provider']=='sagemaker', result
    if service=='fraud': assert result['prediction']=='fraud' and result['risk_score']>0.5
    if service=='forecasting': assert len(result['forecast'])==result['periods']==2
    if service=='recommendations': assert result['user_id']==12 and len(result['recommendations'])==2
    assert response.headers['x-request-id']
    results.append({'service':service,'request_id':response.headers['x-request-id'],'result':result})
print(json.dumps({'path':'deployed frontend -> gateway -> FastAPI -> SageMaker','assets':assets,'probes':probes,'predictions':results},indent=2))
'''
if __name__ == '__main__':
    # Uses kubectl exec to run the check in platform-team, and fails the script if verification
    # fails.
    subprocess.run(['kubectl','-n','platform-team','exec','deployment/gateway-service','--','python','-c',CODE],check=True)
