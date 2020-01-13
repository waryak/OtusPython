import redis
import logging
from typing import Union
from functools import wraps
from redis.exceptions import ConnectionError, TimeoutError


def retry_on_failure(func):
    @wraps(func)
    def wrapper(self, *func_args, **func_kwargs):
        number_of_retries = 0
        while number_of_retries < self.retries_limit:
            try:
                result = func(self, *func_args, **func_kwargs)
                logging.info(msg="Succeded! Result is " + str(result))
                return result
            except (ConnectionError, TimeoutError) as e:
                logging.error("Failed, trying again")
                number_of_retries = number_of_retries + 1
                if number_of_retries >= self.retries_limit:
                    raise e
            except Exception as e:
                raise Exception("Something happened: ", str(e))
    return wrapper


class KeyValueStorage:
    """
    KeyValueStorage wrapper above Reddis with local caching functionality
    and modified "retry" strategy.
    """

    def __init__(self, host: str, port: int, db: int, retries_limit: int, timeout: int):
        """
        db == 1 is for production database
        db == 2 is for test database
        """
        self.host = host
        self.port = port
        self.db = db
        self.timeout = timeout
        self.retries_limit = retries_limit
        self.storage = redis.Redis(host=self.host,
                                   port=self.port,
                                   db=self.db,
                                   socket_connect_timeout=self.timeout)
        self.connect()

    @retry_on_failure
    def connect(self):
        try:
            self.storage.ping()
        except Exception as e:
            logging.error(f"Could not establish connection with exception: {e}")

    @retry_on_failure
    def get(self, key: str) -> Union[str, None]:
        logging.error("FUUCK")
        result = self.storage.get(key)
        return result.decode("utf-8") if result is not None else None

    def get_cache(self, key: str) -> Union[str, None]:
        result = None
        try:
            result = self.storage.get(key)
        except (ConnectionError, TimeoutError):
            logging.error("Could not connect to storage - using cache instead")
        except Exception:
            logging.error("Some strange thing had been encountered")
        return result.decode("utf-8") if result is not None else None

    def set(self, key, value):
        self.storage.set(key, value)
        return True

    def set_cache(self, key, value):
        self.set(key, value)
        return True
