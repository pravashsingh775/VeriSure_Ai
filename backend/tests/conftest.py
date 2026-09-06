# Pytest configuration and fixtures for VeriSure AI
import pytest

from backend.scripts.cleanup_test_artifacts import cleanup


@pytest.fixture(scope='session', autouse=True)
def clean_test_artifacts_after_suite():
    # Teardown: after all tests execute, clean up any test-generated records
    yield
    try:
        cleanup()
    except Exception as exc:
        print(f'Warning: Post-test cleanup encountered an error: {exc}')
