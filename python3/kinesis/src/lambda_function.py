import base64
import datetime as dt
import gzip
import json
import logging
import os
from io import BytesIO

from python3.shipper.shipper import LogzioShipper

# set logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _extract_record_data(data):
    # type: (str) -> bytes
    # The decoded string is returned as a dict. A TypeError is raised if s is
    # incorrectly padded
    try:
        logs_data_decoded = base64.b64decode(data)
    except TypeError as e:
        logger.error("Fail to decode record data: {}".format(str(e)))
        raise

    # if logs come from cloudwatch they will be compressed
    try:
        logs_data_unzipped = gzip.GzipFile(fileobj=BytesIO(logs_data_decoded))
        logs_data_unzipped = logs_data_unzipped.read()
    except (ValueError, OSError) as e:
        logger.warning("Got exception while decompressing: {}".format(e))
        return logs_data_decoded

    return logs_data_unzipped


def _get_type(data):
    # type: (str) -> str
    try:
        return os.environ['TYPE']
    except KeyError:
        return "kinesis_lambda"

    # try:
    #     json_data = json.loads(data)
    #     return json_data["source"].split('.')[1]
    # except (KeyError, ValueError):
    #     return "kinesis_lambda"


def _add_timestamp(log):
    # type: (dict) -> None
    try:
        log['@timestamp'] = dt.datetime.utcfromtimestamp(log['timestamp']).isoformat() + 'Z'
        del log['timestamp']
    except ValueError:
        # If we can't convert to ISO8601 format
        # we will continue without adding @timestamp field
        pass


def _parse_json(log):
    # type: (dict) -> None
    try:
        if os.environ['FORMAT'].lower() == 'json':
            json_object = json.loads(log['message'])
            for k, v in json_object.items():
                log[k] = v
    except (KeyError, ValueError, TypeError):
        pass


def _parse_log_event(log, record):
    log["type"] = _get_type(record)
    _parse_json(log)
    _add_timestamp(log)
    for record_key, record_value in record.items():
        if record_key != "kinesis":
            log[record_key] = record_value


def _extract_logs_from_record(record):
    # type: (dict) -> list
    logs = []
    record_data = _extract_record_data(record["kinesis"]["data"]).decode("utf-8")

    try:
        logs_data = json.loads(record_data)
    except ValueError:
        logs_data = record_data

    try:
        # cw logs
        log_events = logs_data['logEvents']
    except (TypeError, KeyError):
        # let's turn it to a dict
        log_events = [{
            "message": logs_data
        }]

    for log in log_events:
        _parse_log_event(log, record)
        logs.append(log)

    return logs


def lambda_handler(event, context):
    # type: (dict, 'LambdaContext') -> None
    logger.info("Received {} raw Kinesis records.".format(len(event["Records"])))
    try:
        logzio_url = "{0}/?token={1}".format(os.environ['URL'], os.environ['TOKEN'])
    except KeyError as e:
        logger.error("Missing one of the environment variable: {}".format(e))
        raise

    shipper = LogzioShipper(logzio_url)
    for record in event['Records']:
        logs = _extract_logs_from_record(record)
        for log in logs:
            shipper.add(log)

    shipper.flush()
