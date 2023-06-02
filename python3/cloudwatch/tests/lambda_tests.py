import base64
import gzip
import json
import logging
import os
import random
import string
import unittest
from io import BytesIO
from logging.config import fileConfig
import httpretty
import python3.cloudwatch.src.lambda_function as worker

# CONST
BODY_SIZE = 10
STRING_LEN = 10
PYTHON_EVENT_SIZE = 3
NODEJS_EVENT_SIZE = 4

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
        os.environ['TOKEN'] = "123456789"
        os.environ['TYPE'] = "vpcflow"
        self._logzioUrl = "https://listener.logz.io:8071/?token={}".format(os.environ['TOKEN'])

    def tearDown(self):
        if os.environ.get('FORMAT'):
            del os.environ['FORMAT']
        if os.environ.get('COMPRESS'):
            del os.environ['COMPRESS']

    def gzipData(self, data):
        zip_text_file = BytesIO()
        json_data = json.dumps(data).encode('utf-8')
        zipper = gzip.GzipFile(mode='wb', fileobj=zip_text_file)
        zipper.write(json_data)
        zipper.close()
        return base64.b64encode(zip_text_file.getvalue())

    @staticmethod
    # Build random string with STRING_LEN chars
    def _json_string_builder():
        s = string.ascii_lowercase + string.digits
        return json.dumps({
            'timestamp': 'abcd',
            'requestID': 'efgh',
            'message': ''.join(random.sample(s, STRING_LEN))
        })

    @staticmethod
    # Build random string with STRING_LEN chars
    def _json_static_message_string_builder(message):
        return json.dumps({
            'timestamp': 'abcd',
            'requestID': 'efgh',
            'message': message
        })

    @staticmethod
    def _json_nodejs_builder():
        s = string.ascii_lowercase + string.digits
        message = ','.join(random.sample(s, STRING_LEN))
        return "1580747176629\t12345678\tINFO\t" + message

    @staticmethod
    def _json_python_builder():
        s = string.ascii_lowercase + string.digits
        message = ','.join(random.sample(s, STRING_LEN))
        return "1580747176629\t12345678\t" + message

    @staticmethod
    def _random_string_builder():
        s = string.ascii_lowercase + string.digits
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
        data_body = self._data_body_builder(message_builder, body_size)
        enc_data = self.gzipData(data_body)
        event['awslogs']['data'] = enc_data
        return {'dec': data_body, 'enc': event}

    def _validate_json_data(self, request, data, context):
        body_logs_list = request.body.splitlines()
        gen_log_events = data['logEvents']
        for i in range(BODY_SIZE):
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

    def _validate_cloudwatch_log_event(self, request, uniq_message, event_builder, size_of_event):
        original_log = event_builder().split('\t')
        original_log[size_of_event - 1] = uniq_message
        body_logs = json.loads(request.body.decode("utf-8"))
        self.assertEqual(body_logs['@timestamp'], original_log[0])
        self.assertEqual(body_logs['requestID'], original_log[1])

        if 'log_level' in body_logs:
            self.assertEqual(body_logs['log_level'], original_log[2])

        message_list = original_log[size_of_event - 1].split(",")
        original_message_list = body_logs['message'].split(",")

        for i in range(len(message_list)):
            self.assertEqual(message_list[i], original_message_list[i])

    def _test_cloudwatch_format_event(self, event_builder, size_of_event):
        event = {'awslogs': {}}
        data_body = self._data_body_builder(event_builder, 1)
        data_body['logGroup'] = '/aws/lambda/TestlogGroup'
        enc_data = self.gzipData(data_body)
        event['awslogs']['data'] = enc_data
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=200, content_type="application/json")

        try:
            worker.lambda_handler(event, Context)
        except Exception as e:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        uniq_message = data_body['logEvents'][0]['message'].split("\t")[size_of_event - 1]
        request = httpretty.HTTPretty.last_request
        self._validate_cloudwatch_log_event(request, uniq_message, event_builder, size_of_event)

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
        enc_data = self.gzipData(data_body)
        event['awslogs']['data'] = enc_data
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=200, content_type="application/json")
        with self.assertRaises(Exception):
            worker.lambda_handler(event, Context)

    @httpretty.activate
    def test_nodejs_format_event(self):
        self._test_cloudwatch_format_event(self._json_nodejs_builder, NODEJS_EVENT_SIZE)

    @httpretty.activate
    def test_python_format_event(self):
        self._test_cloudwatch_format_event(self._json_python_builder, PYTHON_EVENT_SIZE)

    @httpretty.activate
    def test_json_type_request(self):
        os.environ['FORMAT'] = "json"
        event = self._generate_aws_logs_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        self._validate_json_data(request, event['dec'], Context)

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

        for i in range(BODY_SIZE):
            json_body_log = json.loads(body_logs_list[i])
            self.assertEqual(json_body_log['environment'], "testing")
            self.assertEqual(json_body_log['foo'], "bar")

    @httpretty.activate
    def test_enrich_event_empty(self):
        os.environ['ENRICH'] = ""
        event = self._generate_aws_logs_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        body_logs_list = request.body.splitlines()

        for i in range(BODY_SIZE):
            json_body_log = json.loads(body_logs_list[i])
            self.assertFalse(hasattr(json_body_log, "environment"))

    @httpretty.activate
    def test_enrich_event_bad_format(self):
        os.environ['ENRICH'] = "environment"
        event = self._generate_aws_logs_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")

        with self.assertRaises(IndexError):
            worker.lambda_handler(event['enc'], Context)

    @httpretty.activate
    def test_whitelist_event(self):
        os.environ['WHITELIST'] = "whitelist"
        fixed_string_generated = False

        def event_builder():
            nonlocal fixed_string_generated
            if fixed_string_generated:
                return self._json_string_builder()
            else:
                fixed_string_generated = True
                return self._json_static_message_string_builder("whitelist1")

        event = self._generate_aws_logs_event(event_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        body_logs_list = request.body.splitlines()

        for l in body_logs_list:
            log = json.loads(l)
            self.assertTrue('whitelist' in log['message'])

    @httpretty.activate
    def test_blacklist_event(self):
        os.environ['BLACKLIST'] = "blacklist"
        fixed_string_generated = False

        def event_builder():
            nonlocal fixed_string_generated
            if fixed_string_generated:
                return self._json_string_builder()
            else:
                fixed_string_generated = True
                return self._json_static_message_string_builder("blacklist1")

        event = self._generate_aws_logs_event(event_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body="first", status=200,
                               content_type="application/json")
        try:
            worker.lambda_handler(event['enc'], Context)
        except Exception:
            self.fail("Failed on handling a legit event. Expected status_code = 200")

        request = httpretty.HTTPretty.last_request
        body_logs_list = request.body.splitlines()

        for l in body_logs_list:
            log = json.loads(l)
            self.assertFalse('blacklist' in log['message'])


if __name__ == '__main__':
    unittest.main()
