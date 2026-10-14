"""Optional, best-effort prediction history, separate from inference availability."""
import datetime
import json
import logging
import os
import time
import uuid

import boto3
from botocore.config import Config


class PredictionHistory:
    def __init__(self, service, client=None):
        self.service = service
        self.table = os.getenv('PREDICTION_HISTORY_TABLE', '')
        self.enabled = os.getenv('PREDICTION_HISTORY_ENABLED', 'false').lower() == 'true'
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self._client = client

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client('dynamodb', region_name=self.region,
                config=Config(connect_timeout=1, read_timeout=2,
                              retries={'total_max_attempts': 1}))
        return self._client

    def save(self, request_id, payload, result):
        if not self.enabled:
            return
        try:
            if not self.table:
                raise RuntimeError('History table missing')
            created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
            # A separate event UUID prevents caller-supplied request IDs overwriting records.
            event_id = f'{created_at}#{uuid.uuid4()}'
            self.client.put_item(TableName=self.table, Item={
                'service': {'S': self.service}, 'event_id': {'S': event_id},
                'created_at': {'S': created_at}, 'request_id': {'S': request_id},
                'expires_at': {'N': str(int(time.time()) + 30 * 86400)},
                'payload': {'S': json.dumps(payload, allow_nan=False)},
                'result': {'S': json.dumps(result, allow_nan=False)},
            })
        except Exception as exc:
            # Never log prediction inputs or raw AWS exception messages.
            logging.getLogger('assessment').warning(json.dumps({
                'event': 'prediction_history_write_failed', 'service': self.service,
                'request_id': request_id, 'exception_type': type(exc).__name__}))

    def recent(self, limit):
        if not self.enabled:
            return {'enabled': False, 'items': []}
        if not self.table:
            raise RuntimeError('History table missing')
        response = self.client.query(TableName=self.table,
            KeyConditionExpression='#service = :service',
            ExpressionAttributeNames={'#service': 'service'},
            ExpressionAttributeValues={':service': {'S': self.service}},
            ScanIndexForward=False, Limit=limit, ConsistentRead=True)
        now = int(time.time())
        return {'enabled': True, 'items': [
            {'service': self.service, 'created_at': row['created_at']['S'],
             'request_id': row['request_id']['S'],
             'payload': json.loads(row['payload']['S']),
             'result': json.loads(row['result']['S'])}
            for row in response.get('Items', []) if int(row['expires_at']['N']) > now
        ]}
