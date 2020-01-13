from api import RequestBase
from api import ArgumentsField
import pytest


class RequestWithArgumentField(RequestBase):
    arguments_field = ArgumentsField(required=False, nullable=True)


@pytest.fixture(scope="module")
def arguments_request():
    return RequestWithArgumentField()


def test_argument_not_valid_string(arguments_request):
    with pytest.raises(ValueError):
        arguments_request.arguments_field = 2
        arguments_request._validate()


def test_argument_valid_dict(arguments_request):
    arguments_request.arguments_field = dict(lol="lolvalue", kek="kekvalue")
    assert arguments_request._validate() is True
