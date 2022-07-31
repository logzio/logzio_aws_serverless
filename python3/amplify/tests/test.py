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
# import python3.amplify.src.lambda_function as worker
import amplify.src.lambda_function as worker


# CONST
BODY_SIZE = 10
STRING_LEN = 10
PYTHON_EVENT_SIZE = 3
NODEJS_EVENT_SIZE = 4
FIELDNAMES = ('date', 'time', 'x-edge-location', 'sc-bytes', 'c-ip', 'cs-method', 'cs\(Host)', 'cs-uri-stem', 'sc-status', 'cs\(Referer)', 'cs\(User-Agent)', 'cs-uri-query',	'cs\(Cookie)', 'x-edge-result-type', 'x-edge-request-id', 'x-host-header', 'cs-protocol', 'cs-bytes', 'time-taken',
                      'x-forwarded-for', 'ssl-protocol', 'ssl-cipher', 'x-edge-response-result-type', 'cs-protocol-version', 'fle-status', 'fle-encrypted-fields', 'c-port', 'time-to-first-byte', 'x-edge-detailed-result-type', 'sc-content-type', 'sc-content-len', 'sc-range-start', 'sc-range-end')

RAW_LOG_SAMPLE = ['{"date": "2022-06-13", "time": "13:52:05", "x-edge-location": "TLV50-C2", "sc-bytes": "1024", "c-ip": "80.179.110.98", "cs-method": "GET", "cs\\\\(Host)": "zzz.cloudfront.net", "cs-uri-stem": "/", "sc-status": "200", "cs\\\\(Referer)": "-0", "cs\\\\(User-Agent)": "Mozilla/5.0%20\\\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36", "cs-uri-query": "-0", "cs\\\\(Cookie)": "-0", "x-edge-result-type": "Miss", "x-edge-request-id": "mnKM9AcgsaDFLFGPdIKVgrslLGBBtTWFep2GzhHIIOSXsqiLz5cIHg\\\\=\\\\=", "x-host-header": "master.zzz.amplifyapp.com", "cs-protocol": "https", "cs-bytes": "484", "time-taken": "0.302", "x-forwarded-for": "-0", "ssl-protocol": "TLSv1.3", "ssl-cipher": "TLS_AES_128_GCM_SHA256", "x-edge-response-result-type": "Miss", "cs-protocol-version": "HTTP/2.0", "fle-status": "-0", "fle-encrypted-fields": "-0", "c-port": "50382", "time-to-first-byte": "0.302", "x-edge-detailed-result-type": "Miss", "sc-content-type": "text/html", "sc-content-len": "644", "sc-range-start": "-0", "sc-range-end": "-0"}', '{"date": "2022-06-13", "time": "13:52:06", "x-edge-location": "TLV50-C2", "sc-bytes": "46975", "c-ip": "80.179.110.98", "cs-method": "GET", "cs\\\\(Host)": "zzz.cloudfront.net", "cs-uri-stem": "/static/js/main.39198c94.js", "sc-status": "200", "cs\\\\(Referer)": "https://master.zzz.amplifyapp.com/", "cs\\\\(User-Agent)": "Mozilla/5.0%20\\\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36", "cs-uri-query": "-0", "cs\\\\(Cookie)": "-0", "x-edge-result-type": "Miss", "x-edge-request-id": "0xLaAcHr1ZI5PebBLgB9V7s0Sq3zsxpnyshm00yL-1nMEuP1zTl2-g\\\\=\\\\=", "x-host-header": "master.zzz.amplifyapp.com", "cs-protocol": "https", "cs-bytes": "105", "time-taken": "0.388", "x-forwarded-for": "-0", "ssl-protocol": "TLSv1.3", "ssl-cipher": "TLS_AES_128_GCM_SHA256", "x-edge-response-result-type": "Miss", "cs-protocol-version": "HTTP/2.0", "fle-status": "-0", "fle-encrypted-fields": "-0", "c-port": "50382", "time-to-first-byte": "0.382", "x-edge-detailed-result-type": "Miss", "sc-content-type": "application/javascript", "sc-content-len": "-0", "sc-range-start": "-0", "sc-range-end": "-0"}',
                  '{"date": "2022-06-13", "time": "13:52:06", "x-edge-location": "TLV50-C2", "sc-bytes": "940", "c-ip": "80.179.110.98", "cs-method": "GET", "cs\\\\(Host)": "zzz.cloudfront.net", "cs-uri-stem": "/static/css/main.073c9b0a.css", "sc-status": "200", "cs\\\\(Referer)": "https://master.zzz.amplifyapp.com/", "cs\\\\(User-Agent)": "Mozilla/5.0%20\\\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36", "cs-uri-query": "-0", "cs\\\\(Cookie)": "-0", "x-edge-result-type": "Miss", "x-edge-request-id": "c9PA_psRgmtylwQQpIxBKRHiwhiltFk1aelf9wsapYqH35sTJ08-gQ\\\\=\\\\=", "x-host-header": "master.zzz.amplifyapp.com", "cs-protocol": "https", "cs-bytes": "66", "time-taken": "0.469", "x-forwarded-for": "-0", "ssl-protocol": "TLSv1.3", "ssl-cipher": "TLS_AES_128_GCM_SHA256", "x-edge-response-result-type": "Miss", "cs-protocol-version": "HTTP/2.0", "fle-status": "-0", "fle-encrypted-fields": "-0", "c-port": "50382", "time-to-first-byte": "0.469", "x-edge-detailed-result-type": "Miss", "sc-content-type": "text/css", "sc-content-len": "-0", "sc-range-start": "-0", "sc-range-end": "-0"}', '{"date": "2022-06-13", "time": "14:31:42", "x-edge-location": "TLV50-C2", "sc-bytes": "335", "c-ip": "80.179.110.98", "cs-method": "GET", "cs\\\\(Host)": "zzz.cloudfront.net", "cs-uri-stem": "/manifest.json", "sc-status": "304", "cs\\\\(Referer)": "https://master.zzz.amplifyapp.com/", "cs\\\\(User-Agent)": "Mozilla/5.0%20\\\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36", "cs-uri-query": "-0", "cs\\\\(Cookie)": "-0", "x-edge-result-type": "RefreshHit", "x-edge-request-id": "9YizjAMFz57jXWVOXhEpU20DdWrOcJdMZtxZObp1PLhiAoIHqYr8iw\\\\=\\\\=", "x-host-header": "master.zzz.amplifyapp.com", "cs-protocol": "https", "cs-bytes": "444", "time-taken": "0.273", "x-forwarded-for": "-0", "ssl-protocol": "TLSv1.3", "ssl-cipher": "TLS_AES_128_GCM_SHA256", "x-edge-response-result-type": "RefreshHit", "cs-protocol-version": "HTTP/2.0", "fle-status": "-0", "fle-encrypted-fields": "-0", "c-port": "51112", "time-to-first-byte": "0.273", "x-edge-detailed-result-type": "RefreshHit", "sc-content-type": "-0", "sc-content-len": "-0", "sc-range-start": "-0", "sc-range-end": "-0"}']
DATA_LOG_SAMPLE = [
    {
        "date": "2022-6-13",
        "time": "13:52:05",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "1024",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/",
        "sc-status": "200",
        "cs\\(Referer)": "-",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "mnKM9AcgsaDFLFGPdIKVgrslLGBBtTWFep2GzhHIIOSXsqiLz5cIHg\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "484",
        "time-taken": "0.302",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.302",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "text/html",
        "sc-content-len": "644",
        "sc-range-start": "-",
        "sc-range-end": "-"
    },
    {
        "date": "2022-6-13",
        "time": "13:52:06",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "46975",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/static/js/main.39198c94.js",
        "sc-status": "200",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "0xLaAcHr1ZI5PebBLgB9V7s0Sq3zsxpnyshm00yL-1nMEuP1zTl2-g\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "105",
        "time-taken": "0.388",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.382",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "application/javascript",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",

    },
    {
        "date": "2022-6-13",
        "time": "13:52:06",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "940",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/static/css/main.073c9b0a.css",
        "sc-status": "200",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "c9PA_psRgmtylwQQpIxBKRHiwhiltFk1aelf9wsapYqH35sTJ08-gQ\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "66",
        "time-taken": "0.469",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.469",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "text/css",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-"
    },
    {
        "date": "2022-6-13",
        "time": "14:31:42",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "335",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/manifest.json",
        "sc-status": "304",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "RefreshHit",
        "x-edge-request-id": "9YizjAMFz57jXWVOXhEpU20DdWrOcJdMZtxZObp1PLhiAoIHqYr8iw\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "444",
        "time-taken": "0.273",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "RefreshHit",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "51112",
        "time-to-first-byte": "0.273",
        "x-edge-detailed-result-type": "RefreshHit",
        "sc-content-type": "-",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-"
    },
]


DATA_LOG_SAMPLE_ADDITIONAL_DATA = [
    {
        "date": "2022-6-13",
        "time": "13:52:05",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "1024",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/",
        "sc-status": "200",
        "cs\\(Referer)": "-",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "mnKM9AcgsaDFLFGPdIKVgrslLGBBtTWFep2GzhHIIOSXsqiLz5cIHg\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "484",
        "time-taken": "0.302",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.302",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "text/html",
        "sc-content-len": "644",
        "sc-range-start": "-",
        "sc-range-end": "-",
        "function_version": 1,
        "invoked_function_arn": 1,
                "type": 'logzio_amplify_lambda'

    },
    {
        "date": "2022-6-13",
        "time": "13:52:06",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "46975",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/static/js/main.39198c94.js",
        "sc-status": "200",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "0xLaAcHr1ZI5PebBLgB9V7s0Sq3zsxpnyshm00yL-1nMEuP1zTl2-g\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "105",
        "time-taken": "0.388",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.382",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "application/javascript",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",
        "function_version": 1,
        "invoked_function_arn": 1,
        "type": 'logzio_amplify_lambda'

    },
    {
        "date": "2022-6-13",
        "time": "13:52:06",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "940",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/static/css/main.073c9b0a.css",
        "sc-status": "200",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "c9PA_psRgmtylwQQpIxBKRHiwhiltFk1aelf9wsapYqH35sTJ08-gQ\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "66",
        "time-taken": "0.469",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.469",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "text/css",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",
        "function_version": 1,
        "invoked_function_arn": 1,
        "type": 'logzio_amplify_lambda'

    },
    {
        "date": "2022-6-13",
        "time": "14:31:42",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "335",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/manifest.json",
        "sc-status": "304",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "RefreshHit",
        "x-edge-request-id": "9YizjAMFz57jXWVOXhEpU20DdWrOcJdMZtxZObp1PLhiAoIHqYr8iw\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "444",
        "time-taken": "0.273",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "RefreshHit",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "51112",
        "time-to-first-byte": "0.273",
        "x-edge-detailed-result-type": "RefreshHit",
        "sc-content-type": "-",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",
        "function_version": 1,
        "invoked_function_arn": 1,
        "type": 'logzio_amplify_lambda'
    },
]


DATA_LOG_SAMPLE_UPDATED_TIMESTAMP = [
    {
        "@timestamp": "2022-6-13T13:52:05Z",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "1024",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/",
        "sc-status": "200",
        "cs\\(Referer)": "-",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "mnKM9AcgsaDFLFGPdIKVgrslLGBBtTWFep2GzhHIIOSXsqiLz5cIHg\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "484",
        "time-taken": "0.302",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.302",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "text/html",
        "sc-content-len": "644",
        "sc-range-start": "-",
        "sc-range-end": "-",
                "function_version": 1,
                "invoked_function_arn": 1,
                "type": "logzio_amplify_lambda"
    },
    {
        "@timestamp": "2022-6-13T13:52:06Z",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "46975",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/static/js/main.39198c94.js",
        "sc-status": "200",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "0xLaAcHr1ZI5PebBLgB9V7s0Sq3zsxpnyshm00yL-1nMEuP1zTl2-g\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "105",
        "time-taken": "0.388",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.382",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "application/javascript",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",
                "function_version": 1,
                "invoked_function_arn": 1,
        "type": "logzio_amplify_lambda"

    },
    {
        "@timestamp": "2022-6-13T13:52:06Z",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "940",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/static/css/main.073c9b0a.css",
        "sc-status": "200",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "Miss",
        "x-edge-request-id": "c9PA_psRgmtylwQQpIxBKRHiwhiltFk1aelf9wsapYqH35sTJ08-gQ\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "66",
        "time-taken": "0.469",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "Miss",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "50382",
        "time-to-first-byte": "0.469",
        "x-edge-detailed-result-type": "Miss",
        "sc-content-type": "text/css",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",
                "function_version": 1,
                "invoked_function_arn": 1,
        "type": "logzio_amplify_lambda"

    },
    {
        "@timestamp": "2022-6-13T14:31:42Z",
        "x-edge-location": "TLV50-C2",
        "sc-bytes": "335",
        "c-ip": "80.179.110.98",
        "cs-method": "GET",
        "cs\\(Host)": "zzz.cloudfront.net",
        "cs-uri-stem": "/manifest.json",
        "sc-status": "304",
        "cs\\(Referer)": "https://master.zzz.amplifyapp.com/",
        "cs\\(User-Agent)": "Mozilla/5.0%20\\(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20\\(KHTML%20like%20Gecko)%20Chrome/102.0.0.0%20Safari/537.36",
        "cs-uri-query": "-",
        "cs\\(Cookie)": "-",
        "x-edge-result-type": "RefreshHit",
        "x-edge-request-id": "9YizjAMFz57jXWVOXhEpU20DdWrOcJdMZtxZObp1PLhiAoIHqYr8iw\\=\\=",
        "x-host-header": "master.zzz.amplifyapp.com",
        "cs-protocol": "https",
        "cs-bytes": "444",
        "time-taken": "0.273",
        "x-forwarded-for": "-",
        "ssl-protocol": "TLSv1.3",
        "ssl-cipher": "TLS_AES_128_GCM_SHA256",
        "x-edge-response-result-type": "RefreshHit",
        "cs-protocol-version": "HTTP/2.0",
        "fle-status": "-",
        "fle-encrypted-fields": "-",
        "c-port": "51112",
        "time-to-first-byte": "0.273",
        "x-edge-detailed-result-type": "RefreshHit",
        "sc-content-type": "-",
        "sc-content-len": "-",
        "sc-range-start": "-",
        "sc-range-end": "-",
                "function_version": 1,
                "invoked_function_arn": 1,
        "type": "logzio_amplify_lambda"

    },
]


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

    def test_add_additional_logs(self):
        try:
            for i in range(len(DATA_LOG_SAMPLE)):
                modified_log = worker._get_additional_logs_data(
                    DATA_LOG_SAMPLE[i], Context)
                self.assertEqual(
                    modified_log['function_version'], DATA_LOG_SAMPLE_UPDATED_TIMESTAMP[i]['function_version'])
                self.assertEqual(
                    modified_log['invoked_function_arn'], DATA_LOG_SAMPLE_UPDATED_TIMESTAMP[i]['invoked_function_arn'])
                if os.environ.get('TYPE'):
                    self.assertEqual(
                        modified_log['type'], os.environ.get('TYPE'))
                else:
                    self.assertEqual(
                        modified_log['type'], 'logzio_amplify_lambda')
        except Exception as e:
            self.fail(
                "Additional data is wrong")

    def test_receive_data_from_request_to_array(self):
        try:
            with open('./amplify/tests/data_to_json.txt', "rb") as file_data:

                data = worker.convert_csv_to_array_of_logs(file_data)
                for i in range(len(data)):
                    self.assertEqual(
                        data[i], RAW_LOG_SAMPLE[i])
        except Exception as e:
            self.fail(
                "Fail to conver from data")

    def test_log_receives_right_timestamp(self):
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
