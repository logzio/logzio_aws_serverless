import boto3
import json
import logging
import os
import csv
import datetime
import os.path
import urllib.request

from python3.shipper.shipper import LogzioShipper

FIELD_NAMES = ('date', 'time', 'x-edge-location', 'sc-bytes', 'c-ip', 'cs-method', 'cs\(Host)', 'cs-uri-stem', 'sc-status', 'cs\(Referer)', 'cs\(User-Agent)', 'cs-uri-query',	'cs\(Cookie)', 'x-edge-result-type', 'x-edge-request-id', 'x-host-header', 'cs-protocol', 'cs-bytes', 'time-taken',
               'x-forwarded-for', 'ssl-protocol', 'ssl-cipher', 'x-edge-response-result-type', 'cs-protocol-version', 'fle-status', 'fle-encrypted-fields', 'c-port', 'time-to-first-byte', 'x-edge-detailed-result-type', 'sc-content-type', 'sc-content-len', 'sc-range-start', 'sc-range-end')
DEFAULT_TYPE = 'logzio_amplify_access_lambda'

# set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_amplify_access_log_link(access_logs_starttime, access_logs_endtime):
    # type: (str,str) -> str
    try:

        amplify = boto3.client('amplify')

        result = amplify.generate_access_logs(
            startTime=access_logs_starttime,
            endTime=access_logs_endtime,
            domainName=os.getenv('AMPLIFY_DOMAIN'),
            appId=os.getenv('AMPLIFY_APP_ID')
        )
        return result["logUrl"]
    except Exception as e:
        logger.warning(
            f'Error occurred while trying get access url please check your credentials: {e}.')


def convert_csv_to_array_of_logs(log_url):
    json_array = []

    try:
        response = urllib.request.urlopen(log_url)
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.DictReader(lines, FIELD_NAMES)

        for row in reader:
            json_array.append(json.dumps(row))

        if len(json_array) > 0:
            json_array.pop(0)
    except Exception as e:
        logger.warning(
            f'Error occurred while trying convert csv to array of logs: {e}.')

    return json_array


def _extract_aws_amplify_logs_data(event):
    # type: (dict) -> dict
    event_time = datetime.datetime.strptime(
        event["time"], "%Y-%m-%dT%H:%M:%SZ")
    try:
        access_logs_endtime = event_time

        access_logs_starttime = access_logs_endtime - \
            datetime.timedelta(minutes=5)

        log_url = get_amplify_access_log_link(
            access_logs_starttime, access_logs_endtime)

        logs = convert_csv_to_array_of_logs(log_url)

        return logs

    except ValueError as e:
        logger.error("Got exception while loading json, message: {}".format(e))
        raise ValueError("Exception: json loads")


def _add_timestamp(log):
    # type: (dict) -> dict
    if '@timestamp' not in log:
        timestamp_val = log['date'] + 'T' + log['time'] + 'Z'
        log['@timestamp'] = timestamp_val
        del log['date']
        del log['time']
    return log


def _get_additional_logs_data(log, context):
    # type: (dict, 'LambdaContext') -> dict
    try:
        log['function_version'] = context.function_version
        log['invoked_function_arn'] = context.invoked_function_arn
    except KeyError:
        logger.info(
            'Failed to find context value. Continue without adding it to the log')

    try:
        log['type'] = os.environ['TYPE']
    except KeyError:
        logger.info(f"Using default TYPE {DEFAULT_TYPE}.")
        log['type'] = DEFAULT_TYPE
    return log


def lambda_handler(event, context):
    # type (dict, 'LambdaContext') -> None

    aws_logs_data = _extract_aws_amplify_logs_data(event)
    shipper = LogzioShipper()

    logger.info("About to send {} logs".format(
        len(aws_logs_data)))
    for log in aws_logs_data:
        try:
            json_log = json.loads(log)
        except Exception as e:
            logger.warning(
                f'Error occurred while trying to parse log to JSON: {e}.')
            continue

        json_log = _get_additional_logs_data(json_log, context)
        json_log = _add_timestamp(json_log)
        shipper.add(json_log)

    shipper.flush()
