import gzip
import io
import json
import os
import sys
import time
import urllib
import urllib.request

from python3.custom_logger import custom_logger

# set logger
logger = custom_logger.get_logger(__name__)


class MaxRetriesException(Exception):
    pass


class UnauthorizedAccessException(Exception):
    pass


class BadLogsException(Exception):
    pass


class UnknownURL(Exception):
    pass


class GzipLogRequest(object):

    def __init__(self, max_size_in_bytes):
        self._max_size_in_bytes = max_size_in_bytes
        self._decompress_size = 0
        self._logs_counter = 0
        self._logs = io.BytesIO()
        self._writer = gzip.GzipFile(mode='wb', fileobj=self._logs)
        self._http_headers = {"Content-Encoding": "gzip",
                              "Content-type": "application/json"}

    def __len__(self):
        return self._logs_counter

    def bytes(self):
        return bytes(self._logs.getvalue())

    def write(self, log):
        self._writer.write(bytes(
            "\n" + log, 'utf-8')) if self._logs_counter else self._writer.write(bytes(log, 'utf-8'))
        self._logs_counter += 1

    def reset(self):
        self._decompress_size = 0
        self._logs_counter = 0
        self._logs.truncate(0)
        self._writer = gzip.GzipFile(mode='wb', fileobj=self._logs)

    def decompress_size(self):
        return self._decompress_size

    def compress_size(self):
        old_file_position = self._logs.tell()
        self._logs.seek(0, os.SEEK_END)
        self._logs.seek(0, os.SEEK_END)
        size = self._logs.tell()
        self._logs.seek(old_file_position, os.SEEK_SET)
        return size

    def close(self):
        self._writer.close()

    def flush(self):
        self._writer.flush()

    def http_headers(self):
        return self._http_headers


class StringLogRequest(object):

    def __init__(self, max_size_in_bytes):
        self._max_size_in_bytes = max_size_in_bytes
        self._size = 0
        self._logs = []
        self._http_headers = {"Content-type": "application/json"}

    def __len__(self):
        return len(self._logs)

    def bytes(self):
        str_logs = "\n".join(self._logs)
        return bytes(str_logs, 'utf-8')

    # String
    def write(self, log):
        self._logs.append(log)
        self._size += sys.getsizeof(log)

    def reset(self):
        self._size = 0
        self._logs = []

    def compress_size(self):
        return self._size

    def decompress_size(self):
        return self._size

    def close(self):
        pass

    def flush(self):
        pass

    def http_headers(self):
        return self._http_headers


class LogzioShipper(object):
    MAX_BULK_SIZE_IN_BYTES = 3 * 1024 * 1024
    ACCOUNT_TOKEN_ENV = 'TOKEN'
    REGION_ENV = 'REGION'
    URL_ENV = 'LISTENER_URL'
    BASE_URL = "https://listener.logz.io:8071"
    region = None
    TIMEOUT_ENV = 'REQUEST_TIMEOUT'
    default_timeout = 15  # seconds

    def __init__(self):
        self._logzio_url = self.BASE_URL

        if os.environ.get(self.URL_ENV):
            self._logzio_url = os.environ.get(self.URL_ENV)
            logger.warning(
                "Environment variable URL is deprecated and will not be supported in the future. Use REGION instead")

        if os.environ.get(self.REGION_ENV):
            self.region = os.environ.get(self.REGION_ENV)
            self._logzio_url = self.get_base_api_url()
        try:
            self._logzio_url = "{0}/?token={1}".format(
                self._logzio_url, os.environ[self.ACCOUNT_TOKEN_ENV])
        except KeyError as e:
            logger.error(
                "Missing logz.io account token environment variable: {}".format(e))
            raise
        try:
            self._compress = os.environ['COMPRESS'].lower() == "true"
        except KeyError as e:
            self._compress = False
        self._logs = GzipLogRequest(self.MAX_BULK_SIZE_IN_BYTES) \
            if self._compress \
            else StringLogRequest(self.MAX_BULK_SIZE_IN_BYTES)

        self.timeout = self._get_timeout()

    def _get_timeout(self):
        timeout_str = os.getenv(self.TIMEOUT_ENV)
        if timeout_str != '':
            try:
                timeout = int(timeout_str)
                if timeout > 0:
                    return timeout
                logger.warning(f'Timeout input from user is invalid, reverting to default value {self.default_timeout}')
            except ValueError:
                logger.warning(f'Could not parse timeout input {timeout_str}, reverting to default value {self.default_timeout}')
        return self.default_timeout

    def get_base_api_url(self):
        return self.BASE_URL.replace("listener.", "listener{}.".format(self.get_region_code()))

    def get_region_code(self):
        if self.region != "us" and self.region != "":
            return "-{}".format(self.region)
        return ""

    def add(self, log):
        # type (dict) -> None
        json_log = json.dumps(log)
        self._logs.write(json_log)
        # To prevent flush() after every log added
        if self._logs.decompress_size() > self.MAX_BULK_SIZE_IN_BYTES:
            self._logs.flush()
            self._try_to_send()

    def _reset(self):
        self._logs.reset()

    def _try_to_send(self):
        if self._logs.compress_size() > self.MAX_BULK_SIZE_IN_BYTES:
            self._send_to_logzio()
            self._reset()

    def flush(self):
        if self._logs.compress_size():
            self._logs.flush()
            self._send_to_logzio()
            self._reset()

    @staticmethod
    def retry(func):
        def retry_func():
            max_retries = 4
            sleep_between_retries = 2

            for retries in range(max_retries):
                if retries:
                    sleep_between_retries *= 2
                    logger.info("Failure in sending logs - Trying again in {} seconds"
                                .format(sleep_between_retries))
                    time.sleep(sleep_between_retries)
                try:
                    res = func()
                except urllib.error.HTTPError as e:
                    status_code = e.getcode()
                    if status_code == 400:
                        raise BadLogsException(e.reason)
                    elif status_code == 401:
                        raise UnauthorizedAccessException()
                    elif status_code == 404:
                        raise UnknownURL()
                    else:
                        logger.error("Unknown HTTP exception: {}".format(e))
                        continue
                except urllib.error.URLError:
                    raise
                return res

            raise MaxRetriesException()

        return retry_func

    def _send_to_logzio(self):
        @LogzioShipper.retry
        def do_request():
            self._logs.close()
            logs = self._logs.bytes()
            logger.info(f'About to send {len(logs)} bytes')
            request = urllib.request.Request(self._logzio_url, data=self._logs.bytes(),
                                             headers=self._logs.http_headers())
            return urllib.request.urlopen(request, timeout=self.timeout)

        try:
            do_request()
            logger.info(
                "Successfully sent bulk of {} logs to Logz.io!".format(len(self._logs)))
        except MaxRetriesException:
            logger.error('Retry limit reached. Failed to send log entry.')
            raise MaxRetriesException()
        except BadLogsException as e:
            logger.error("Got 400 code from Logz.io. This means that some of your logs are too big, "
                         "or badly formatted. response: {0}".format(e))
            logger.warning("Dropping logs that cause the bad response...")
        except UnauthorizedAccessException:
            logger.error(
                "You are not authorized with Logz.io! Token OK? dropping logs...")
            raise UnauthorizedAccessException()
        except UnknownURL:
            logger.error("Please check your url...")
            raise UnknownURL()
        except urllib.error.HTTPError as e:
            logger.error(
                "Unexpected error while trying to send logs: {}".format(e))
            raise
        except Exception as e:
            logger.error(e)
            raise
