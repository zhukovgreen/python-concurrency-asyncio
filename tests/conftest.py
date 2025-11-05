import pytest


@pytest.fixture(autouse=True)
def prepend_3_new_lines():
    print("\n\n\n")
    yield
