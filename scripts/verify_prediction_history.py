"""Exercise the deployed frontend/API/SageMaker/DynamoDB path for all services."""
import subprocess

CODE = '''
import json, time, urllib.request
base = 'http://frontend-service.platform-team.svc.cluster.local/api'
samples = {
 'fraud': {'amount':1800,'transaction_count':35,'account_age_days':12},
 'forecasting': {'values':[10,20,30],'periods':2},
 'recommendations': {'user_id':12,'category':'electronics','limit':2},
}
rows = []
for service, payload in samples.items():
 request = urllib.request.Request(base+'/'+service+'/predict', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
 response = urllib.request.urlopen(request, timeout=90)
 result = json.load(response)
 assert result['provider'] == 'sagemaker', result
 request_id = response.headers['x-request-id']
 saved = None
 for attempt in range(15):
  history = json.load(urllib.request.urlopen(base+'/'+service+'/history?limit=50', timeout=10))
  assert history['enabled'], history
  saved = next((row for row in history['items'] if row['request_id'] == request_id), None)
  if saved: break
  time.sleep(1)
 assert saved, 'Prediction not found in DynamoDB history: '+service
 assert saved['payload'] == payload and saved['result'] == result, saved
 rows.append({'service':service,'request_id':request_id,'created_at':saved['created_at'],'provider':result['provider'],'persisted':True})
print(json.dumps({'path':'deployed frontend -> gateway -> API -> SageMaker + DynamoDB history', 'checks':rows}, indent=2))
'''

if __name__ == '__main__':
    subprocess.run(['kubectl', '-n', 'platform-team', 'exec',
                    'deployment/gateway-service', '--', 'python', '-c', CODE], check=True)
