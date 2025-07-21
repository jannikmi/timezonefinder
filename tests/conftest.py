"""
Configuration file for pytest.
"""


def pytest_configure(config):
    """
    Register custom markers for different types of tests.
    """
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
