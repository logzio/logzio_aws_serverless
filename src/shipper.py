import gzip
import json
import logging
import sys
import time
import urllib2
import StringIO
import os

# set logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        self._logs = StringIO.StringIO()
        self._writer = gzip.GzipFile(mode='wb', fileobj=self._logs)
        self._http_headers = {"Content-Encoding": "gzip", "Content-type": "application/json"}

    def __len__(self):
        return self._logs_counter

    def __str__(self):
        return self._logs.getvalue()

    def write(self, log):
        self._writer.write("\n" + log) if self._decompress_size else self._writer.write(log)
        self._decompress_size += sys.getsizeof(log)
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

    def __str__(self):
        return '\n'.join(self._logs)

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

    def __init__(self, logzio_url):
        self._logzio_url = logzio_url
        try:
            self._compress = os.environ['COMPRESS'].lower() == "true"
        except KeyError:
            self._compress = False
        self._logs = GzipLogRequest(self.MAX_BULK_SIZE_IN_BYTES) \
            if self._compress \
            else StringLogRequest(self.MAX_BULK_SIZE_IN_BYTES)

    def add(self, log):
        # type: (dict) -> None
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

            for retries in xrange(max_retries):
                if retries:
                    sleep_between_retries *= 2
                    logger.info("Failure in sending logs - Trying again in {} seconds"
                                .format(sleep_between_retries))
                    time.sleep(sleep_between_retries)
                try:
                    res = func()
                except urllib2.HTTPError as e:
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
                except urllib2.URLError:
                    raise
                return res

            raise MaxRetriesException()

        return retry_func

    def _send_to_logzio(self):
        @LogzioShipper.retry
        def do_request():
            self._logs.close()
            request = urllib2.Request(self._logzio_url, data=str(self._logs), headers=self._logs.http_headers())
            return urllib2.urlopen(request)

        try:
            do_request()
            logger.info("Successfully sent bulk of {} logs to Logz.io!".format(len(self._logs)))
        except MaxRetriesException:
            logger.error('Retry limit reached. Failed to send log entry.')
            raise MaxRetriesException()
        except BadLogsException as e:
            logger.error("Got 400 code from Logz.io. This means that some of your logs are too big, "
                         "or badly formatted. response: {0}".format(e.message))
            raise BadLogsException()
        except UnauthorizedAccessException:
            logger.error("You are not authorized with Logz.io! Token OK? dropping logs...")
            raise UnauthorizedAccessException()
        except UnknownURL:
            logger.error("Please check your url...")
            raise UnknownURL()
        except urllib2.HTTPError as e:
            logger.error("Unexpected error while trying to send logs: {}".format(e))
            raise
        except Exception as e:
            logger.error(e)
            raise
