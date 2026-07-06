import os
import pytest

def pytest_configure(config):
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://vyapar_local:change-this-local-development-password@127.0.0.1:5433/vyapar_pulse_test"
    )
    if "test" not in database_url.lower():
        raise RuntimeError("Test database must contain 'test' in database name for isolation.")
