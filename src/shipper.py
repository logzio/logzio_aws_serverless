import gzip
import json
import logging
import sys
import time
import urllib2
import StringIO

# set logger
import os

import zlib

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


class LogzioShipper(object):
    MAX_BULK_SIZE_IN_BYTES = 3 * 1024 * 1024

    def __init__(self, logzio_url):
        self._decompress_size = 0
        self._logs = StringIO.StringIO()
        self._logzio_url = logzio_url
        self._logs_counter = 0
        try:
            self._compress = os.environ['COMPRESS'].lower() in ["yes", "true", "t", "1"]
        except KeyError:
            self._compress = False
        self._writer = self._create_new_writer()

    def _create_new_writer(self):
        self._logs.truncate(0)
        return gzip.GzipFile(mode='wb', fileobj=self._logs) if self._compress else self._logs

    def add(self, log):
        # type: (dict) -> None
        json_log = json.dumps(log)
        self._writer.write("\n" + json_log) if self._decompress_size else self._writer.write(json_log)
        self._logs_counter += 1
        self._decompress_size += sys.getsizeof(json_log)
        # To prevent flush() after every log added
        if self._decompress_size > self.MAX_BULK_SIZE_IN_BYTES:
            self._writer.flush()
            self._try_to_send()

    def _reset(self):
        self._decompress_size = 0
        self._logs_counter = 0
        self._writer = self._create_new_writer()

    def _try_to_send(self):
        if self._log_size() > self.MAX_BULK_SIZE_IN_BYTES:
            self._send_to_logzio()
            self._reset()

    def flush(self):
        if self._log_size():
            self._writer.flush()
            self._send_to_logzio()
            self._reset()

    def close(self):
        self._writer.close()
        self._logs.close()

    def _log_size(self):
        old_file_position = self._logs.tell()
        self._logs.seek(0, os.SEEK_END)
        size = self._logs.tell()
        self._logs.seek(old_file_position, os.SEEK_SET)
        return size

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
            headers = {"Content-type": "application/json"}
            if self._compress:
                headers["Content-Encoding"] = "gzip"
                self._writer.close()
            request = urllib2.Request(self._logzio_url, self._logs.getvalue(), headers=headers)
            return urllib2.urlopen(request)

        try:
            do_request()
            logger.info("Successfully sent bulk of {} logs to Logz.io!".format(self._logs_counter))
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
