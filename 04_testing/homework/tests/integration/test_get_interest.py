import pytest
from scoring import get_interests
from redis import ConnectionError, TimeoutError


def test_get_score_with_valid(working_storage):
    result = get_interests(working_storage, 1)
    assert result == ["women", "money", "power"]
    result = get_interests(working_storage, 2)
    assert result == [420]


def test_get_score_with_broken(broken_storage):
    with pytest.raises( (ConnectionError, TimeoutError) ):
        result = get_interests(broken_storage, 1)



