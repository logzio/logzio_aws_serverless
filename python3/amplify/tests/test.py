import base64
import gzip
import json
import logging
import os
import csv
import random
import string
import unittest
from io import BytesIO
from logging.config import fileConfig
import httpretty
import amplify.src.lambda_function as worker
from test_data import DATA_LOG_SAMPLE, DATA_LOG_SAMPLE_ADDITIONAL_DATA, RAW_LOG_SAMPLE, DATA_LOG_SAMPLE_UPDATED_TIMESTAMP

# CONST
BODY_SIZE = 10
STRING_LEN = 10
PYTHON_EVENT_SIZE = 3
NODEJS_EVENT_SIZE = 4
FIELDNAMES = ('date', 'time', 'x-edge-location', 'sc-bytes', 'c-ip', 'cs-method', 'cs\(Host)', 'cs-uri-stem', 'sc-status', 'cs\(Referer)', 'cs\(User-Agent)', 'cs-uri-query',	'cs\(Cookie)', 'x-edge-result-type', 'x-edge-request-id', 'x-host-header', 'cs-protocol', 'cs-bytes', 'time-taken',
                      'x-forwarded-for', 'ssl-protocol', 'ssl-cipher', 'x-edge-response-result-type', 'cs-protocol-version', 'fle-status', 'fle-encrypted-fields', 'c-port', 'time-to-first-byte', 'x-edge-detailed-result-type', 'sc-content-type', 'sc-content-len', 'sc-range-start', 'sc-range-end')


fileConfig('amplify/tests/logging_config.ini')
logger = logging.getLogger(__name__)


class Context(object):
    function_version = 1
    invoked_function_arn = 1
    memory_limit_in_mb = 128


class TestLambdaFunction(unittest.TestCase):
    """ Unit testing logzio lambda function """

    def setUp(self):
        # Set os.environ for tests
        os.environ['TOKEN'] = "123456789"
        os.environ['TYPE'] = "vpcflow"
        self._logzioUrl = "https://listener.logz.io:8071/?token={}".format(
            os.environ['TOKEN'])

    def test_get_additional_logs_data(self):
        try:
            for i in range(len(DATA_LOG_SAMPLE)):
                modified_log = worker._get_additional_logs_data(
                    DATA_LOG_SAMPLE[i], Context)
                self.assertEqual(
                    modified_log['function_version'], DATA_LOG_SAMPLE_ADDITIONAL_DATA[i]['function_version'])
                self.assertEqual(
                    modified_log['invoked_function_arn'], DATA_LOG_SAMPLE_ADDITIONAL_DATA[i]['invoked_function_arn'])
                if os.environ.get('TYPE'):
                    self.assertEqual(
                        modified_log['type'], os.environ.get('TYPE'))
                else:
                    self.assertEqual(
                        modified_log['type'], 'logzio_amplify_lambda')
        except Exception as e:
            self.fail(
                "Additional data is wrong")

    def test_convert_csv_to_array_of_logs(self):
        try:
            with open('./amplify/tests/data_to_json.txt', "rb") as file_data:

                data = worker.convert_csv_to_array_of_logs(file_data)
                for i in range(len(data)):
                    self.assertEqual(
                        data[i], RAW_LOG_SAMPLE[i])
        except Exception as e:
            self.fail(
                "Fail to conver from data")

    def test_add_timestamp(self):
        try:
            for i in range(len(DATA_LOG_SAMPLE)):
                modified_log = worker._add_timestamp(DATA_LOG_SAMPLE[i])
                self.assertEqual(
                    modified_log['@timestamp'], DATA_LOG_SAMPLE_UPDATED_TIMESTAMP[i]['@timestamp'])
        except Exception as e:
            self.fail(
                "Added timestamp is failed")


if __name__ == '__main__':
    unittest.main()
