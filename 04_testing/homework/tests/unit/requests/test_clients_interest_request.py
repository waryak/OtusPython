import pytest


def test_argument_not_valid_string(valid_clients_interest_request):
    assert valid_clients_interest_request._validate() is True


def test_argument_valid_dict(invalid_clients_interest_request):
    with pytest.raises(ValueError):
        invalid_clients_interest_request._validate()
