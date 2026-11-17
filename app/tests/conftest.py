"""Bridge the existing script-style assertion collectors into pytest.

Legacy @run_test wrappers catch assertions and append TestResult objects. A
plain list fixture would turn failures into false passes; check it on teardown.
"""
import pytest


@pytest.fixture
def results():
    records = []
    yield records
    failures = [f"{r.name}: {r.message}" for r in records if not r.passed]
    assert not failures, "\n".join(failures)


@pytest.fixture
def tmp(tmp_path):
    """Legacy export scripts use the name tmp for a temporary directory."""
    return tmp_path
