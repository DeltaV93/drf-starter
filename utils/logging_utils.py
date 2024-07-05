import logging
import sys
from functools import wraps
import time

# Configure the root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,  # This ensures logs are sent to stdout
)


def get_logger(name):
    """
    Get a logger with the specified name.

    :param name: Usually __name__ of the module
    :return: Logger instance
    """
    return logging.getLogger(name)


def log_exception(logger):
    """
    A decorator to log exceptions raised in functions.

    :param logger: The logger instance to use
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {str(e)}")
                raise

        return wrapper

    return decorator


def timed_function(logger):
    """
    A decorator to log the execution time of functions.

    :param logger: The logger instance to use
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"{func.__name__} took {end_time - start_time:.2f} seconds to execute.")
            return result

        return wrapper

    return decorator


class RequestLogger:
    """
    A class to log incoming HTTP requests and their responses.
    """

    def __init__(self, logger):
        self.logger = logger

    def log_request(self, request):
        self.logger.info(f"Received {request.method} request to {request.path}")

    def log_response(self, response, request):
        self.logger.info(f"Responded to {request.method} request to {request.path} with status {response.status_code}")


def sanitize_log_data(data):
    """
    Remove sensitive information from data before logging.

    :param data: Dict containing data to be logged
    :return: Dict with sensitive information removed
    """
    sensitive_fields = ['password', 'token', 'api_key']
    return {k: '****' if k in sensitive_fields else v for k, v in data.items()}
