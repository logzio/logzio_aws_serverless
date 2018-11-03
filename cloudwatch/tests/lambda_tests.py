import base64
import gzip
import httpretty
import json
import logging
import os
import random
import cloudwatch.src.lambda_function as worker
import string
import unittest

from logging.config import fileConfig
from shipper.shipper import MaxRetriesException, UnauthorizedAccessException, BadLogsException, UnknownURL
from StringIO import StringIO

# CONST
BODY_SIZE = 10
STRING_LEN = 10

fileConfig('logging_config.ini')
logger = logging.getLogger(__name__)


class Context(object):
    function_version = 1
    invoked_function_arn = 1
    memory_limit_in_mb = 128


class TestLambdaFunction(unittest.TestCase):
    """ Unit testing logzio lambda function """
    def setUp(self):
        # Set os.environ for tests
        os.environ['URL'] = "https://listener.logz.io:8071"
        os.environ['TOKEN'] = "123456789"
        os.environ['TYPE'] = "vpcflow"
        self._logzioUrl = "{0}/?token={1}".format(os.environ['URL'], os.environ['TOKEN'])

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

    @staticmethod
    # Create aws data json format string
    def _data_body_builder(message_builder, body_size):
        data_body = {'logStream': 'TestStream', 'messageType': 'DATA_MESSAGE', 'logEvents': []}

        # Each awslog event contain BODY_SIZE messages
        for i in range(body_size):
            log = {"timestamp": "i", "message": message_builder(), "id": i}
            data_body['logEvents'].append(log)

        data_body['owner'] = 'Test'
        data_body['subscriptionFilters'] = ['TestFilters']
        data_body['logGroup'] = 'TestlogGroup'
        return data_body

    # Encrypt and zip the data as awslog format require
    def _generate_aws_logs_event(self, message_builder, body_size=BODY_SIZE):
        event = {'awslogs': {}}

        data = self._data_body_builder(message_builder, body_size)
        zip_text_file = StringIO()
        zipper = gzip.GzipFile(mode='wb', fileobj=zip_text_file)
        zipper.write(json.dumps(data))
        zipper.close()
        enc_data = base64.b64encode(zip_text_file.getvalue())

        event['awslogs']['data'] = enc_data
        return {'dec': data, 'enc': event}

    # Verify the data
    def _check_data(self, request, data, context):
        buf = StringIO(request.body)
        try:
            body = gzip.GzipFile(mode='rb', fileobj=buf) if request.headers['Content-Encoding'] == 'gzip' else buf
        except KeyError:
            body = buf

        body_logs_list = body.readlines()
        gen_log_events = data['logEvents']

        for i in xrange(BODY_SIZE):
            json_body_log = json.loads(body_logs_list[i])
            logger.debug("bodyLogsList[{2}]: {0} Vs. genLogEvents[{2}]: {1}"
                        .format(json.loads(body_logs_list[i])['message'], gen_log_events[i]['message'], i))
            self.assertEqual(json_body_log['function_version'], context.function_version)
            self.assertEqual(json_body_log['invoked_function_arn'], context.invoked_function_arn)
            self.assertEqual(json_body_log['@timestamp'], gen_log_events[i]['timestamp'])
            self.assertEqual(json_body_log['id'], gen_log_events[i]['id'])
            self.assertEqual(json_body_log['message'], gen_log_events[i]['message'])
            self.assertEqual(json_body_log['type'], os.environ['TYPE'])

    def _check_json_data(self, request, data, context):
        body_logs_list = request.body.splitlines()
        gen_log_events = data['logEvents']

        for i in xrange(BODY_SIZE):
            json_body_log = json.loads(body_logs_list[i])
            logger.debug("bodyLogsList[{2}]: {0} Vs. genLogEvents[{2}]: {1}".
                         format(json.loads(body_logs_list[i])['message'], gen_log_events[i]['message'], i))

            self.assertEqual(json_body_log['function_version'], context.function_version)
            self.assertEqual(json_body_log['invoked_function_arn'], context.invoked_function_arn)
            self.assertEqual(json_body_log['@timestamp'], gen_log_events[i]['timestamp'])
            self.assertEqual(json_body_log['id'], gen_log_events[i]['id'])
            self.assertEqual(json_body_log['type'], os.environ['TYPE'])
            json_message = json.loads(gen_log_events[i]['message'])
            for key, value in json_message.items():
                self.assertEqual(json_body_log[key], value)

    @httpretty.activate
    def test_bad_request(self):
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, responses=[
                                httpretty.Response(body="first", status=400),
                                httpretty.Response(body="second", status=401),
                            ])
        with self.assertRaises(BadLogsException):
            worker.lambda_handler(event['enc'], Context)

        with self.assertRaises(UnauthorizedAccessException):
            worker.lambda_handler(event['enc'], Context)

    @httpretty.activate
    def test_ok_request(self):
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        self._check_data(request, event['dec'], Context)

    @httpretty.activate
    def test_ok_gzip_request(self):
        os.environ['COMPRESS'] = 'true'
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            assert "Failed on handling a legit event. Expected status_code = 200"

        request = httpretty.HTTPretty.last_request
        self._check_data(request, event['dec'], Context)

    @httpretty.activate
    def test_gzip_typo_request(self):
        os.environ['COMPRESS'] = 'fakecompress'
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
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
        event = self._generate_aws_logs_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        self._check_json_data(request, event['dec'], Context)

    @httpretty.activate
    def test_retry_request(self):
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, responses=[
                                httpretty.Response(body="1st Fail", status=500),
                                httpretty.Response(body="2nd Fail", status=500),
                                httpretty.Response(body="3rd Success", status=200)
                            ])
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Should have succeeded on last try")

        request = httpretty.HTTPretty.last_request
        self._check_data(request, event['dec'], Context)

    @httpretty.activate
    def test_retry_limit(self):
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=500)
        with self.assertRaises(MaxRetriesException):
            worker.lambda_handler(event['enc'], Context)

    @httpretty.activate
    def test_bad_url(self):
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=404)
        with self.assertRaises(UnknownURL):
            worker.lambda_handler(event['enc'], Context)

    @httpretty.activate
    def test_wrong_format_event(self):
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

        with self.assertRaises(TypeError):
            worker.lambda_handler(event, Context)

    @httpretty.activate
    def test_large_body(self):
        body_size = 2000
        event = self._generate_aws_logs_event(self._random_string_builder, body_size)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        last_bulk_length = len(request.body.splitlines())
        assert last_bulk_length <= 2000, "Logs were not fragmented"

    @httpretty.activate
    def test_enrich_event(self):
        os.environ['ENRICH'] = "environment=testing;foo=bar"
        event = self._generate_aws_logs_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        body_logs_list = request.body.splitlines()

        for i in xrange(BODY_SIZE):
            json_body_log = json.loads(body_logs_list[i])
            self.assertEqual(json_body_log['environment'], "testing")
            self.assertEqual(json_body_log['foo'], "bar")


if __name__ == '__main__':
    unittest.main()
