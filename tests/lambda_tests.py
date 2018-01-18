import base64
import datetime
import gzip
import httpretty
import json
import logging
import os
import random
import string
import unittest

from logging.config import fileConfig
from src.lambda_function import lambda_handler as handler
from StringIO import StringIO

## CONST
BODYSIZE = 10
STRINGLEN = 10

# create logger assuming running from ./run script
fileConfig('tests/logging_config.ini')
logger = logging.getLogger(__name__)

class TestLambdaFunction(unittest.TestCase):
    """ Unit testing logzio lambda function """

    def setUp(self):
        # Set os.environ for tests
        os.environ['URL'] = "https://listener.logz.io:8071"
        os.environ['TOKEN'] = "123456789"
        os.environ['TYPE'] = "vpcflow"
        self._logzioUrl = "{0}/?token={1}&type={2}".format(os.environ['URL'], os.environ['TOKEN'], os.environ['TYPE'])

    # Build random string with STRINGLEN chars
    def _random_string_builder(self):
        s = string.lowercase + string.digits
        return ''.join(random.sample(s, STRINGLEN))

    # Build random string with STRINGLEN chars
    def _json_string_builder(self):
        s = string.lowercase + string.digits
        return json.dumps({
                'field1': 'abcd',
                'field2': 'efgh',
                'message': ''.join(random.sample(s, STRINGLEN))
            })

    # Create aws data json format string
    def _data_body_builder(self, message_builder):
        dataBody = {}
        dataBody['logStream'] = 'TestStream'
        dataBody['messageType'] = 'DATA_MESSAGE'

        dataBody['logEvents'] = []
        # Each awslog event contain BODYSIZE messages
        for i in range(BODYSIZE):
            log = { "timestamp" : i,
                    "message" : message_builder(),
                    "id" : i
            }
            dataBody['logEvents'].append(log)

        dataBody['owner'] = 'Test'
        dataBody['subscriptionFilters'] = ['TestFilters']
        dataBody['logGroup'] = 'TestlogGroup'
        return dataBody

    # Encrypt and zip the data as awslog format require
    def _generate_aws_logs_event(self, message_builder):
        event = {}
        event['awslogs'] = {}

        data = self._data_body_builder(message_builder)
        zipTextFile = StringIO()
        zipper = gzip.GzipFile(mode='wb', fileobj=zipTextFile)
        zipper.write(json.dumps(data))
        zipper.close()
        encData =  base64.b64encode(zipTextFile.getvalue())

        event['awslogs']['data'] = encData
        return {'dec': data, 'enc': event}

    # Verify the data the moke got and the data we created are equal
    def _checkData(self, request, data):
        bodyLogsList = request.body.splitlines()

        genLogEvents = data['logEvents']

        for i in xrange(BODYSIZE):
            jsonBodyLog = json.loads(bodyLogsList[i])
            logger.info("bodyLogsList[{2}]: {0} Vs. genLogEvents[{2}]: {1}".format(json.loads(bodyLogsList[i])['message'],\
                                                                                genLogEvents[i]['message'], i))

            self.assertEqual(jsonBodyLog['timestamp'], genLogEvents[i]['timestamp'])
            self.assertEqual(jsonBodyLog['id'], genLogEvents[i]['id'])
            self.assertEqual(jsonBodyLog['message'], genLogEvents[i]['message'])

    def _checkJsonData(self, request, data):
        bodyLogsList = request.body.splitlines()

        genLogEvents = data['logEvents']

        for i in xrange(BODYSIZE):
            jsonBodyLog = json.loads(bodyLogsList[i])
            logger.info("bodyLogsList[{2}]: {0} Vs. genLogEvents[{2}]: {1}".format(json.loads(bodyLogsList[i])['message'],\
                                                                                genLogEvents[i]['message'], i))

            self.assertEqual(jsonBodyLog['timestamp'], genLogEvents[i]['timestamp'])
            self.assertEqual(jsonBodyLog['id'], genLogEvents[i]['id'])
            json_message = json.loads(genLogEvents[i]['message'])
            for key, value in json_message.items():
                self.assertEqual(jsonBodyLog[key], value)

    @httpretty.activate
    def test_bad_request(self):
        logger.info("TEST: test_bad_request")
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, responses=[
                                httpretty.Response(body = "first", status=400),
                                httpretty.Response(body = "second", status=401),
                            ])

        with self.assertRaises(IOError):
            handler(event['enc'],None)
        logger.info("Catched the correct exception. Status code = 400")

        with self.assertRaises(IOError):
            handler(event['enc'],None)
        logger.info("Catched the correct exception. Status code = 401")

    @httpretty.activate
    def test_ok_request(self):
        logger.info("TEST: test_ok_request")
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body = "first", status=200, content_type="application/json")

        try:
            handler(event['enc'],None)
        except Exception:
            assert True,"Failed on handling a legit event. Expected status_code = 200"

        request = httpretty.HTTPretty.last_request
        self._checkData(request, event['dec'])

    @httpretty.activate
    def test_json_type_request(self):
        logger.info("TEST: test_json_request")
        os.environ['TYPE'] = "JSON"
        event = self._generate_aws_logs_event(self._json_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body = "first", status=200, content_type="application/json")

        try:
            handler(event['enc'],None)
        except Exception:
            assert True,"Failed on handling a legit event. Expected status_code = 200"

        request = httpretty.HTTPretty.last_request
        self._checkJsonData(request, event['dec'])

    @httpretty.activate
    def test_malformed_json_type_request(self):
        logger.info("TEST: test_json_request")
        os.environ['TYPE'] = "JSON"
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, body = "first", status=200, content_type="application/json")

        try:
            handler(event['enc'],None)
        except Exception:
            assert True,"Failed on handling a legit event. Expected status_code = 200"

        request = httpretty.HTTPretty.last_request
        self._checkData(request, event['dec'])

    @httpretty.activate
    def test_retry_request(self):
        logger.info("TEST: test_retry_request")
        event = self._generate_aws_logs_event(self._random_string_builder)
        httpretty.register_uri(httpretty.POST, self._logzioUrl, responses=[
                                httpretty.Response(body = "1st Fail", status=500),
                                httpretty.Response(body = "2nd Fail", status=500),
                                httpretty.Response(body = "3rd Success", status=200)
                            ])
        try:
            handler(event['enc'],None)
        except Exception:
            assert True,"Should have succeeded on last try"

        request = httpretty.HTTPretty.last_request
        self._checkData(request, event['dec'])

    @httpretty.activate
    def test_wrong_format_event(self):
        logger.info("TEST: test_wrong_format_event")

        event = {}
        event['awslogs'] = {}
        dataBody = {}
        dataBody['logStream'] = 'TestStream'
        dataBody['messageType'] = 'DATA_MESSAGE'

        dataBody['logEvents'] = []
        # Adding wrong format log
        log = "{'timestamp' : '10', 'message' : 'wrong_format', 'id' : '10'}"
        dataBody['logEvents'].append(log)
        dataBody['owner'] = 'Test'
        dataBody['subscriptionFilters'] = ['TestFilters']
        dataBody['logGroup'] = 'TestlogGroup'

        zipTextFile = StringIO()
        zipper = gzip.GzipFile(mode='wb', fileobj=zipTextFile)
        zipper.write(json.dumps(dataBody))
        zipper.close()
        encData =  base64.b64encode(zipTextFile.getvalue())

        event['awslogs']['data'] = encData
        httpretty.register_uri(httpretty.POST, self._logzioUrl, status=200, content_type="application/json")

        with self.assertRaises(TypeError):
            handler(event,None)
        logger.info("Catched the correct exception, wrong format message")

if __name__ == '__main__':
    unittest.main()
