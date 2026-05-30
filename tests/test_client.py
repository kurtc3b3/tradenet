from unittest.mock import Mock

import httpx

from tradenet.comtrade.client import _retry_after_seconds


def test_retry_after_seconds_uses_api_message():
    response = Mock(spec=httpx.Response)
    response.headers = {}
    response.json.return_value = {
        "statusCode": 429,
        "message": "Rate limit is exceeded. Try again in 2 seconds.",
    }
    assert _retry_after_seconds(response, attempt=0) == 2.0


def test_retry_after_seconds_uses_retry_after_header():
    response = Mock(spec=httpx.Response)
    response.headers = {"Retry-After": "3"}
    response.json.return_value = {}
    assert _retry_after_seconds(response, attempt=0) == 3.0


def test_retry_after_seconds_falls_back_to_exponential_backoff():
    response = Mock(spec=httpx.Response)
    response.headers = {}
    response.json.return_value = {"message": "Rate limit is exceeded."}
    assert _retry_after_seconds(response, attempt=2) == 4.0
