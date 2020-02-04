import gzip
import json
import logging
import os
from python3.shipper.shipper import LogzioShipper
import base64
from io import BytesIO

KEY_INDEX = 0
VALUE_INDEX = 1
LOG_LEVELS = ['alert', 'trace', 'debug', 'notice', 'info', 'warn',
              'warning', 'error', 'err', 'critical', 'crit', 'fatal',
              'severe', 'emerg', 'emergency']

python_event_size = 3
nodejs_event_size = 4


# set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _extract_aws_logs_data(event):
    # type: (dict) -> dict
    event_str = event['awslogs']['data']
    try:
        logs_data_decoded = base64.b64decode(event_str)
        logs_data_unzipped = gzip.GzipFile(fileobj=BytesIO(logs_data_decoded))
        logs_data_unzipped = logs_data_unzipped.read()
        logs_data_dict = json.loads(logs_data_unzipped)
        return logs_data_dict
    except ValueError as e:
        logger.error("Got exception while loading json, message: {}".format(e))
        raise ValueError("Exception: json loads")


def _extract_lambda_log_message(log):
    str_message = str(log['message'])
    try:
        start_level = str_message.index('[')
        end_level = str_message.index(']')
        log_level = str_message[start_level + 1:end_level]
        if log_level.lower() in LOG_LEVELS:
            log['log_level'] = log_level
        start_split = end_level + 2
    except ValueError:
        # Let's try without log level
        start_split = 0

    message_parts = str_message[start_split:].split('\t')
    size = len(message_parts)
    if size == python_event_size or size == nodejs_event_size:
        log['@timestamp'] = message_parts[0]
        log['requestID'] = message_parts[1]
        log['message'] = message_parts[size - 1]
    if size == nodejs_event_size:
        log['log_level'] = message_parts[2]


def _put_timestamp(log):
    if '@timestamp' not in log:
        log['@timestamp'] = str(log['timestamp'])
        del log['timestamp']


def _parse_to_json(log):
    try:
        if os.environ['FORMAT'].lower() == 'json':
            json_object = json.loads(log['message'])
            for key, value in json_object.items():
                log[key] = value
    except (KeyError, ValueError) as e:
        pass


def _parse_cloudwatch_log(log, additional_data):
    # type: (dict, dict) -> None
    _put_timestamp(log)
    if '/aws/lambda/' in additional_data['logGroup']:
        if _is_valid_log(log):
            _extract_lambda_log_message(log)
        else:
            return False
    log.update(additional_data)
    _parse_to_json(log)
    return True


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
        logger.info("Using default TYPE 'logzio_cloudwatch_lambda'.")
        additional_data['type'] = 'logzio_cloudwatch_lambda'
    return additional_data


def _is_valid_log(log):
    try:
        if log['message'].startswith('START') or log['message'].startswith('END') or log['message'].startswith('REPORT'):
            return False
    except Exception as e:
        pass
    return True


def lambda_handler(event, context):
    # type (dict, 'LambdaContext') -> None
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
        if _parse_cloudwatch_log(log, additional_data):
            shipper.add(log)

    shipper.flush()