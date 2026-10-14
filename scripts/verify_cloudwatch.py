"""Verify project CloudWatch configuration and fresh deployed request-log ingestion."""
import datetime
import json
import subprocess
import time
import uuid

import boto3

REGION = 'us-east-1'
PREFIX = 'anthony-assessment4'
CLUSTER = PREFIX + '-eks'
LOG_GROUP = f'/aws/containerinsights/{CLUSTER}/application'


def main():
    session = boto3.Session(region_name=REGION)
    eks, logs, cw = [session.client(name) for name in ('eks', 'logs', 'cloudwatch')]
    addon = eks.describe_addon(clusterName=CLUSTER, addonName='amazon-cloudwatch-observability')['addon']
    assert addon['status'] == 'ACTIVE', addon['status']
    assert not addon.get('health', {}).get('issues'), addon.get('health')
    enabled = {kind for entry in eks.describe_cluster(name=CLUSTER)['cluster']['logging']['clusterLogging']
               if entry['enabled'] for kind in entry['types']}
    assert enabled == {'api', 'audit', 'authenticator', 'controllerManager', 'scheduler'}, enabled
    dashboard = cw.get_dashboard(DashboardName=PREFIX + '-operations')
    assert len(json.loads(dashboard['DashboardBody'])['widgets']) >= 7
    alarms = cw.describe_alarms(AlarmNamePrefix=PREFIX + '-')['MetricAlarms']
    assert len(alarms) == 12 and all(a['ActionsEnabled'] and a['AlarmActions'] for a in alarms)
    sample = json.dumps({'log_processed': {'status': 502}})
    assert logs.test_metric_filter(filterPattern='{ $.log_processed.status >= 500 }', logEventMessages=[sample])['matches']
    assert not logs.test_metric_filter(filterPattern='{ $.log_processed.status >= 500 }',
        logEventMessages=[json.dumps({'log_processed': {'status': 200}})])['matches']
    assert logs.test_metric_filter(filterPattern='{ $.log_processed.event = "prediction_history_write_failed" }',
        logEventMessages=[json.dumps({'log_processed': {'event': 'prediction_history_write_failed'}})])['matches']

    marker = 'cw-verify-' + str(uuid.uuid4())
    start = int(time.time() * 1000) - 10000
    # Real health requests traverse frontend, gateway, and all three downstream APIs.
    code = """import urllib.request
base='http://frontend-service.platform-team.svc.cluster.local/api'
for service in ['fraud','forecasting','recommendations']:
 r=urllib.request.urlopen(urllib.request.Request(base+'/'+service+'/health',headers={'x-request-id':MARKER}),timeout=10)
 assert r.status==200
""".replace('MARKER', repr(marker))
    subprocess.run(['kubectl', '-n', 'platform-team', 'exec', 'deployment/gateway-service', '--', 'python', '-c', code], check=True)
    services = set()
    for attempt in range(36):
        events = logs.filter_log_events(logGroupName=LOG_GROUP, startTime=start, filterPattern='"' + marker + '"')['events']
        for event in events:
            row = json.loads(event['message'])
            service = row.get('log_processed', {}).get('service')
            if service:
                services.add(service)
        if {'fraud', 'forecasting', 'recommendations', 'gateway'} <= services:
            break
        time.sleep(5)
    assert {'fraud', 'forecasting', 'recommendations', 'gateway'} <= services, services
    # Frontend nginx access logs contain /api/... paths; health has access logging disabled.
    events = logs.filter_log_events(logGroupName=LOG_GROUP, startTime=start,
        filterPattern='{ $.kubernetes.container_name = "frontend" }', limit=20)['events']
    assert events, 'Frontend nginx access logs not received'
    group = logs.describe_log_groups(logGroupNamePrefix=LOG_GROUP)['logGroups'][0]
    assert group['retentionInDays'] == 14
    now = datetime.datetime.now(datetime.timezone.utc)
    metric_samples = {}
    for name in ('node_cpu_utilization', 'node_memory_utilization',
                 'pod_number_of_running_containers', 'pod_number_of_container_restarts'):
        datapoints = cw.get_metric_statistics(Namespace='ContainerInsights', MetricName=name,
            Dimensions=[{'Name': 'ClusterName', 'Value': CLUSTER}],
            StartTime=now - datetime.timedelta(minutes=15), EndTime=now,
            Period=60, Statistics=['Average'])['Datapoints']
        assert datapoints, 'Container Insights metric has no samples yet: ' + name
        metric_samples[name] = len(datapoints)
    control_streams = logs.describe_log_streams(logGroupName=f'/aws/eks/{CLUSTER}/cluster',
        orderBy='LastEventTime', descending=True, limit=10)['logStreams']
    assert any(stream.get('lastEventTimestamp') for stream in control_streams)
    print(json.dumps({'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'addon_status': addon['status'], 'control_plane_log_types': sorted(enabled),
        'dashboard': dashboard['DashboardName'], 'alarms': [a['AlarmName'] for a in alarms],
        'application_log_services': sorted(services), 'frontend_access_logs_received': True,
        'metric_filters_checked': True, 'container_insights_metric_samples': metric_samples,
        'control_plane_logs_received': True, 'request_id': marker, 'retention_days': 14}, indent=2))


if __name__ == '__main__':
    main()
