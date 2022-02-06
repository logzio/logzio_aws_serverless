#!/bin/bash

## TIMESTAMP IS IN UTC
NOW_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
LOGS=$(printf '{"messageType":"DATA_MESSAGE","owner":"123456789123","logGroup":"testLogGroup","logStream":"testLogStream","subscriptionFilters":["testFilter"],"logEvents":[{"id":"eventId1","timestamp":"%s","message":"[ERROR] Logz.io cloudwatch test log1"},{"id":"eventId2","timestamp":"%s","message":"[ERROR] Logz.io cloudwatch test log2"}]}' $NOW_TIMESTAMP $NOW_TIMESTAMP)
DATA=""
if [[ "$OSTYPE" == "darwin"* ]]; then
        DATA=$(echo $LOGS | gzip | base64)
else
        DATA=$(echo $LOGS | gzip | base64 -w0)
fi
TEST_EVENT=$(printf '{
  "awslogs": {
    "data": "%s"
  }
}' $DATA)
echo $TEST_EVENT