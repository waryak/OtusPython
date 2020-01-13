import json
import pytest
import smtplib

from api import ClientsInterestsRequest
from store import KeyValueStorage

RETRIES_LIMIT = 2
TIMEOUT = 1


@pytest.fixture(scope="module")
def valid_clients_interest_request():
    return ClientsInterestsRequest(**{"client_ids": 1, "date": "01.01.2001"})


@pytest.fixture(scope="module", params=[{"client_ids": 3, "date": "01-01-2001"}, {"client_ids": "ass", "date": "02.02.2002"}])
def invalid_clients_interest_request(request):
    return ClientsInterestsRequest(**request.param)


@pytest.fixture(scope="module")
def smtp_connection():
    return smtplib.SMTP("smtp.gmail.com", 587, timeout=5)


@pytest.fixture(scope="module")
def working_storage():
    kvs = KeyValueStorage(host="0.0.0.0",
                          port=6379,
                          db=2,
                          retries_limit=RETRIES_LIMIT,
                          timeout=TIMEOUT)
    kvs.set("KEY", "LOLKEY")
    kvs.set("LOLKEY", "LOLVALUE")
    kvs.set("i:1", json.dumps(["women", "money", "power"]))
    kvs.set("i:2", json.dumps([420]))
    return kvs


@pytest.fixture(scope="module")
def broken_storage():
    kvs = KeyValueStorage(host="1.0.1.0",
                          port=6379,
                          db=2,
                          retries_limit=RETRIES_LIMIT,
                          timeout=TIMEOUT)
    return kvs
