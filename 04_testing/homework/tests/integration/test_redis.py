def test_set_get(working_storage):
    result = working_storage.get("LOLKEY")
    assert result == "LOLVALUE"


def test_get_absent(working_storage):
    assert working_storage.get("TOLERANCE") is None


