import base64
import json
import logging
import os
import datetime as dt

from shipper.shipper import LogzioShipper

# set logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _extract_record_data(data):
    # type: (str) -> str
    # The decoded string is returned. A TypeError is raised if s is
    # incorrectly padded
    try:
        return base64.b64decode(data)
    except TypeError as e:
        logger.error("Fail to decode record data: {}".format(e.message))
        raise


def _parse_json(log, record_data):
    # type: (dict, str) -> None
    log.update(json.loads(record_data))


def _add_record_kinesis_fields(log, record_kinesis_field):
    # type: (dict, dict) -> None
    for key, value in record_kinesis_field.items():
        if key == "data":
            record_data = _extract_record_data(value)
            # If FORMAT is json treat message as a json
            try:
                if os.environ["FORMAT"].lower() == "json":
                    _parse_json(log, record_data)
            except (KeyError, ValueError):
                # Put data as a string
                log["message"] = record_data
        elif key == "approximateArrivalTimestamp":
            try:
                log["@timestamp"] = dt.datetime.utcfromtimestamp(value).isoformat() + 'Z'
            except ValueError:
                # If we can't convert to ISO8601 format
                # we will continue without adding @timestamp field
                pass
        else:
            log[key] = value


def _parse_kinesis_record(record):
    # type: (dict, str) -> dict
    try:
        log = {"type": os.environ['TYPE']}
    except KeyError:
        log = {"type": "kinesis_lambda"}

    for record_key, record_value in record.items():
        if record_key == "kinesis":
            _add_record_kinesis_fields(log, record_value)
        else:
            log[record_key] = record_value
    return log


def lambda_handler(event, context):
    # type: (dict, 'LambdaContext') -> None
    # kinesis event:
    # {
    #     "Records": [
    #         {
    #             "kinesis": {
    #                 "partitionKey": "partitionKey-03",
    #                 "kinesisSchemaVersion": "1.0",
    #                 "data": "SGVsbG8sIHRoaXMgaXMgYSB0ZXN0IDEyMy4=",
    #                 "sequenceNumber": "49545115243490985018280067714973144582180062593244200961",
    #                 "approximateArrivalTimestamp": 1539783387.44
    #             },
    #             "eventSource": "aws:kinesis",
    #             "eventID": "shardId-000000000000:49545115243490985018280067714973144582180062593244200961",
    #             "invokeIdentityArn": "arn:aws:iam::EXAMPLE",
    #             "eventVersion": "1.0",
    #             "eventName": "aws:kinesis:record",
    #             "eventSourceARN": "arn:aws:kinesis:EXAMPLE",
    #             "awsRegion": "us-east-1"
    #         }
    #     ]
    # }
    logger.info("Received {} raw Kinesis records.".format(len(event["Records"])))
    try:
        logzio_url = "{0}/?token={1}".format(os.environ['URL'], os.environ['TOKEN'])
    except KeyError as e:
        logger.error("Missing one of the environment variable: {}".format(e))
        raise

    shipper = LogzioShipper(logzio_url)
    for record in event['Records']:
        log = _parse_kinesis_record(record)
        shipper.add(log)

    shipper.flush()
