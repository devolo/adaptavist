"""Helper methods used by the tests."""

import os


def load_fixture(filename: str):
    """Load a fixture."""
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path, encoding="utf-8") as fp:
        return fp.read()
