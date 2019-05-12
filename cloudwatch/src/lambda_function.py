import gzip
import json
import logging
import os

from shipper.shipper import LogzioShipper
from StringIO import StringIO

KEY_INDEX = 0
VALUE_INDEX = 1
LOG_LEVELS = ['alert', 'trace', 'debug', 'notice', 'info', 'warn',
          'warning', 'error', 'err', 'critical', 'crit', 'fatel',
          'severe', 'emerg', 'emergency']

# set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _extract_aws_logs_data(event):
    # type: (dict) -> dict
    try:
        logs_data_decoded = event['awslogs']['data'].decode('base64')
        logs_data_unzipped = gzip.GzipFile(fileobj=StringIO(logs_data_decoded)).read()
        logs_data_dict = json.loads(logs_data_unzipped)
        return logs_data_dict
    except ValueError as e:
        logger.error("Got exception while loading json, message: {}".format(e))
        raise ValueError("Exception: json loads")


def _extract_lambda_log_message(log, log_group):
    # Lambda function log message looks like this:
    # "[LEVEL]\t2017-04-26T10:41:09.023Z\tdb95c6da-2a6c-11e7-9550-c91b65931beb\tloading index.html...\n"
    # but there are START, END and REPORT messages too:
    # "START RequestId: 67c005bb-641f-11e6-b35d-6b6c651a2f01 Version: 31\n"
    # "END RequestId: 5e665f81-641f-11e6-ab0f-b1affae60d28\n"
    # "REPORT RequestId: 5e665f81-641f-11e6-ab0f-b1affae60d28\tDuration: 1095.52 ms\tBilled Duration: 1100 ms \tMemory Size
    if '/aws/lambda/' in log_group:
        str_message = str(log['message'])
        if str_message.startswith('START') \
                or str_message.startswith('END') \
                or str_message.startswith('REPORT'):
            return

        try:
            start_level = str_message.index('[')
            end_level = str_message.index(']')
            log_level = str_message[start_level+1:end_level]
            if log_level.lower() in LOG_LEVELS:
                log['log_level'] = log_level
            start_split = end_level + 2
        except ValueError:
            # Let's try without log level
            start_split = 0

        message_parts = str_message[start_split:].split('\t')
        if len(message_parts) == 3:
            log['@timestamp'] = message_parts[0]
            log['requestID'] = message_parts[1]
            log['message'] = message_parts[2]


def _parse_cloudwatch_log(log, additional_data):
    # type: (dict, dict) -> None
    if '@timestamp' not in log:
        log['@timestamp'] = str(log['timestamp'])
        del log['timestamp']

    _extract_lambda_log_message(log, additional_data['logGroup'])
    log.update(additional_data)

    # If FORMAT is json treat message as a json
    try:
        if os.environ['FORMAT'].lower() == 'json':
            json_object = json.loads(log['message'])
            for key, value in json_object.items():
                log[key] = value
    except (KeyError, ValueError):
        pass


def _get_additional_logs_data(aws_logs_data, context):
    # type: (dict, 'LambdaContext') -> dict
    additional_fields = ['logGroup', 'logStream', 'messageType', 'owner']
    additional_data = dict((key, aws_logs_data[key]) for key in additional_fields)
    try:
        additional_data['function_version'] = context.function_version
        additional_data['invoked_function_arn'] = context.invoked_function_arn
    except KeyError:
        logger.info('Failed to find context value. Continue without adding it to the log')

    try:
        # If ENRICH has value, add the properties
        if os.environ['ENRICH']:
            properties_to_enrich = os.environ['ENRICH'].split(";")
            for property_to_enrich in properties_to_enrich:
                property_key_value = property_to_enrich.split("=")
                additional_data[property_key_value[KEY_INDEX]] = property_key_value[VALUE_INDEX]
    except KeyError:
        pass

    try:
        additional_data['type'] = os.environ['TYPE']
    except KeyError:
        logger.info("Failed to find 'TYPE' environment variables. Using 'logzio_cloudwatch_lambda' instead")
        additional_data['type'] = 'logzio_cloudwatch_lambda'

    return additional_data


def lambda_handler(event, context):
    # type: (dict, 'LambdaContext') -> None
    try:
        logzio_url = "{0}/?token={1}".format(os.environ['URL'], os.environ['TOKEN'])
    except KeyError as e:
        logger.error("Missing one of the environment variable: {}".format(e))
        raise

    aws_logs_data = _extract_aws_logs_data(event)
    additional_data = _get_additional_logs_data(aws_logs_data, context)
    shipper = LogzioShipper(logzio_url)

    logger.info("About to send {} logs".format(len(aws_logs_data['logEvents'])))
    for log in aws_logs_data['logEvents']:
        if not isinstance(log, dict):
            raise TypeError("Expected log inside logEvents to be a dict but found another type")

        _parse_cloudwatch_log(log, additional_data)
        shipper.add(log)

    shipper.flush()
