import base64
import copy
import gzip
import httpretty
import json
import logging
import os
import random

import kinesis.src.lambda_function as worker
import string
import unittest

from logging.config import fileConfig
from shipper.shipper import MaxRetriesException, UnauthorizedAccessException, BadLogsException, UnknownURL
from StringIO import StringIO

# CONST
RECORD_SIZE = 10
STRING_LEN = 10

_record_body = {
    'eventSource': 'aws:kinesis',
    'eventID': 'shardId-000000000000:49545115243490985018280067714973144582180062593244200961',
    'invokeIdentityArn': 'arn:aws:iam::TEST',
    'eventVersion': '1.0',
    'eventName': 'aws:kinesis:record',
    'eventSourceARN': 'arn:aws:kinesis:TEST',
    'awsRegion': 'us-east-1',
}

_kinesis_data = {
    'partitionKey': 'partitionKey-03',
    'kinesisSchemaVersion': '1.0',
    'sequenceNumber': '49545115243490985018280067714973144582180062593244200961',
    'approximateArrivalTimestamp': 1539783387.44,
}

fileConfig('logging_config.ini')
logger = logging.getLogger(__name__)


class TestLambdaFunction(unittest.TestCase):
    """ Unit testing logzio lambda function """
    def setUp(self):
        # Set os.environ for tests
        os.environ['URL'] = "https://listener.logz.io:8071"
        os.environ['TOKEN'] = "123456789"
        os.environ['TYPE'] = "logzio_kinesis"
        self._logzioUrl = "{0}/?token={1}".format(os.environ['URL'], os.environ['TOKEN'])
        self._dec_data = []

    def tearDown(self):
        if os.environ.get('FORMAT'):
            del os.environ['FORMAT']
        if os.environ.get('COMPRESS'):
            del os.environ['COMPRESS']

    @staticmethod
    # Build random string with STRING_LEN chars
    def _json_string_builder():
        s = string.lowercase + string.digits
        return json.dumps({
                'field1': 'abcd',
                'field2': 'efgh',
                'message': ''.join(random.sample(s, STRING_LEN))
            })

    @staticmethod
    def _random_string_builder():
        s = string.lowercase + string.digits
        return ''.join(random.sample(s, STRING_LEN))

    def _kinesis_record_builder(self, message_builder):
        record_body = copy.deepcopy(_record_body)

        dec_data = message_builder()
        try:
            self._dec_data.append(json.loads(dec_data)['message'])
        except ValueError:
            self._dec_data.append(dec_data)

        kinesis_data = copy.deepcopy(_kinesis_data)
        kinesis_data['data'] = base64.b64encode(dec_data)
        record_body['kinesis'] = kinesis_data
        return record_body

    def _generate_kinesis_event(self, message_builder):
        return {'Records': [self._kinesis_record_builder(message_builder) for _ in xrange(RECORD_SIZE)]}

    def _validate_data(self, request):
        buf = StringIO(request.body)
        try:
            body = gzip.GzipFile(mode='rb', fileobj=buf) if request.headers['Content-Encoding'] == 'gzip' else buf
        except KeyError:
            body = buf

        body_logs_list = body.readlines()
        for i in xrange(RECORD_SIZE):
            json_body_log = json.loads(body_logs_list[i])
            # print(json_body_log)
            for key, value in json_body_log.items():
                if key == '@timestamp':
                    pass
                elif key == 'message':
                    self.assertIn(value, self._dec_data)
                elif key == 'type':
                    self.assertEqual(value, os.environ['TYPE'])
                elif key in _record_body:
                    self.assertEqual(_record_body[key], value)
                elif key in _kinesis_data:
                    self.assertEqual(_kinesis_data[key], value)
                elif os.environ['FORMAT'].lower() == 'json':
                    self.assertIn('field1', json_body_log)
                    self.assertEqual(json_body_log['field1'], 'abcd')
                    self.assertIn('field2', json_body_log)
                    self.assertEqual(json_body_log['field2'], 'efgh')
                else:
                    print(key)
                    self.fail("Failed to find key in the original event")

    @httpretty.activate
    def test_bad_request(self):
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, responses=[
                                httpretty.Response(body="first", status=400),
                                httpretty.Response(body="second", status=401),
                            ])

        with self.assertRaises(BadLogsException):
            worker.lambda_handler(event, None)

        with self.assertRaises(UnauthorizedAccessException):
            worker.lambda_handler(event, None)

    @httpretty.activate
    def test_ok_request(self):
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event, None)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        self._validate_data(request)

    @httpretty.activate
    def test_ok_gzip_request(self):
        os.environ['COMPRESS'] = 'true'
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event, None)
        except Exception:
            assert "Failed on handling a legit event. Expected status_code = 200"

        request = httpretty.HTTPretty.last_request
        self._validate_data(request)

    @httpretty.activate
    def test_gzip_typo_request(self):
        os.environ['COMPRESS'] = 'fakecompress'
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event, None)
        except Exception:
            assert "Failed on handling a legit event. Expected status_code = 200"

        request = httpretty.HTTPretty.last_request
        try:
            gzip_header = request.headers["Content-Encoding"]
            self.fail("Failed to send uncompressed logs with typo in compress env filed")
        except KeyError:
            pass

    @httpretty.activate
    def test_json_type_request(self):
        os.environ['FORMAT'] = "JSON"
        event = self._generate_kinesis_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event, None)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        self._validate_data(request)

    @httpretty.activate
    def test_retry_request(self):
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, responses=[
                                httpretty.Response(body="1st Fail", status=500),
                                httpretty.Response(body="2nd Fail", status=500),
                                httpretty.Response(body="3rd Success", status=200)
                            ])
        try:
            worker.lambda_handler(event, None)
        except Exception:
            self.fail("Should have succeeded on last try")

        request = httpretty.HTTPretty.last_request
        self._validate_data(request)

    @httpretty.activate
    def test_retry_limit(self):
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=500)

        with self.assertRaises(MaxRetriesException):
            worker.lambda_handler(event, None)

    @httpretty.activate
    def test_bad_url(self):
        event = self._generate_kinesis_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=404)

        with self.assertRaises(UnknownURL):
            worker.lambda_handler(event, None)

    @httpretty.activate
    def test_wrong_event(self):
        event = {'awslogs': {}}
        data_body = {'logStream': 'TestStream', 'messageType': 'DATA_MESSAGE', 'logEvents': []}

        # Adding wrong format log
        log = "{'timestamp' : '10', 'message' : 'wrong_format', 'id' : '10'}"
        data_body['logEvents'].append(log)
        data_body['owner'] = 'Test'
        data_body['subscriptionFilters'] = ['TestFilters']
        data_body['logGroup'] = 'TestlogGroup'

        zip_text_file = StringIO()
        zipper = gzip.GzipFile(mode='wb', fileobj=zip_text_file)
        zipper.write(json.dumps(data_body))
        zipper.close()
        enc_data = base64.b64encode(zip_text_file.getvalue())

        event['awslogs']['data'] = enc_data
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=200, content_type="application/json")

        with self.assertRaises(KeyError):
            worker.lambda_handler(event, None)


if __name__ == '__main__':
    unittest.main()
