import logging

import pytest

from utils.logging_utils import REDACTED, log_exception, sanitize_log_data, timed_function

logger = logging.getLogger(__name__)


def test_sensitive_keys_are_redacted():
    sanitized = sanitize_log_data({'username': 'ada', 'password': 'hunter2'})

    assert sanitized == {'username': 'ada', 'password': REDACTED}


def test_redaction_is_case_insensitive():
    assert sanitize_log_data({'Password': 'hunter2'})['Password'] == REDACTED


def test_redaction_recurses_into_nested_dicts():
    sanitized = sanitize_log_data({'user': {'name': 'ada', 'token': 'abc'}})

    assert sanitized['user']['token'] == REDACTED
    assert sanitized['user']['name'] == 'ada'


def test_non_dicts_pass_through():
    assert sanitize_log_data('not a dict') == 'not a dict'


def test_log_exception_reraises(caplog):
    @log_exception(logger)
    def boom():
        raise ValueError('nope')

    with pytest.raises(ValueError), caplog.at_level(logging.ERROR):
        boom()

    assert 'boom' in caplog.text


def test_timed_function_returns_the_value():
    @timed_function(logger)
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_timed_function_logs_even_when_the_call_fails(caplog):
    @timed_function(logger, level=logging.INFO)
    def boom():
        raise ValueError('nope')

    with pytest.raises(ValueError), caplog.at_level(logging.INFO):
        boom()

    assert 'boom took' in caplog.text
