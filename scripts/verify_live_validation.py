# Brings in the libraries, shared code, and test or runtime settings needed below.
"""Check malformed-request responses through deployed frontend/gateway/services."""
import subprocess

# Defines a small Python program to execute inside the deployed gateway pod; these checks use real
# Service DNS addresses.
CODE = '''import json, urllib.request, urllib.error
base='http://frontend-service.platform-team.svc.cluster.local'
results=[]
def check(url, body):
    request=urllib.request.Request(url,data=body.encode(),headers={'Content-Type':'application/json','X-Request-ID':'validation-regression-check'})
    try:
        response=urllib.request.urlopen(request,timeout=90)
        raise AssertionError('Expected 422, got '+str(response.status))
    except urllib.error.HTTPError as error:
        payload=json.loads(error.read())
        assert error.code==422, (url,error.code,payload)
        assert error.headers['x-request-id']=='validation-regression-check'
        assert 'Traceback' not in json.dumps(payload)
        results.append({'url':url,'status':error.code,'response':payload})
for service in ['fraud','forecasting','recommendations']:
    check(base+'/api/'+service+'/predict','{"nested":[NaN]}')
    body={'fraud':'{"amount":NaN,"transaction_count":1,"account_age_days":1}', 'forecasting':'{"values":[Infinity],"periods":2}', 'recommendations':'{"user_id":NaN,"category":"electronics","limit":2}'}[service]
    check('http://'+service+'-service.'+service+'-team.svc.cluster.local/predict',body)
check(base+'/api/recommendations/predict','{"user_id":1,"category":"unknown","limit":2}')
print(json.dumps({'checks':results},indent=2))
'''
if __name__ == '__main__':
    # Uses kubectl exec to run the check in platform-team, and fails the script if verification
    # fails.
    subprocess.run(['kubectl','-n','platform-team','exec','deployment/gateway-service','--','python','-c',CODE],check=True)
