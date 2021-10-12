import base64
import datetime as dt
import json
import logging
import os
import copy
import gzip
import binascii

from python3.shipper.shipper import LogzioShipper

# set logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
MESSAGES_ARRAY_ENV = 'MESSAGES_ARRAY'


def _extract_record_data(data):
    # type: (str) -> str
    # The decoded string is returned. A TypeError is raised if s is
    # incorrectly padded
    try:
        # decompress the payload if it looks gzippy
        decoded = base64.b64decode(data)
        if binascii.hexlify(decoded[0:2]) == b'1f8b':
            return gzip.decompress(decoded)
        else:
            return decoded
    except TypeError as e:
        logger.error("Fail to decode record data: {}".format(str(e)))
        raise


def _parse_json(log, record_data):
    # type: (dict, str) -> None
    log.update(json.loads(record_data))


def _get_type(data):
    # type: (str) -> str
    try:
        return os.environ['TYPE']
    except KeyError:
        pass

    try:
        json_data = json.loads(data)
        return json_data["source"].split('.')[1]
    except (KeyError, ValueError):
        return "kinesis_lambda"


def _add_record_kinesis_fields(log, record_kinesis_field):
    # type: (dict, dict) -> None
    for key, value in record_kinesis_field.items():
        if key == "data":
            record_data = _extract_record_data(value)
            # If FORMAT is json treat message as a json
            try:
                if os.environ["FORMAT"].lower() == "json":
                    _parse_json(log, record_data)
                else:
                    log["message"] = record_data
            except (KeyError, ValueError):
                # Put data as a string
                log["message"] = record_data
            log["type"] = _get_type(record_data)
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
    log = {}
    for record_key, record_value in record.items():
        if record_key == "kinesis":
            _add_record_kinesis_fields(log, record_value)
        else:
            log[record_key] = record_value
    return log


def split_by_fields(log, field):
    logs = []
    for msg in log[field]:
        temp_log = copy.deepcopy(log)
        temp_log.update(msg)
        temp_log.pop(field)
        logs.append(temp_log)
    return logs

def lambda_handler(event, context):
    # type: (dict, 'LambdaContext') -> None
    logger.info("Received {} raw Kinesis records.".format(len(event["Records"])))
    multiple_msgs = os.environ.get(MESSAGES_ARRAY_ENV)

    shipper = LogzioShipper()
    for record in event['Records']:
        log = _parse_kinesis_record(record)
        if multiple_msgs and multiple_msgs in log:
            logs = split_by_fields(log, multiple_msgs)
        else:
            try:
                log["message"] = log["message"].decode("utf-8")
            except UnicodeDecodeError:
                data = gzip.decompress(log["message"])
                log["message"] = data.decode('utf-8')
            except (AttributeError, KeyError):
                pass
            logs = [log]
        for log in logs:
            shipper.add(log)

    shipper.flush()
