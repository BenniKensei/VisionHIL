"""
Session-scoped fixtures for the VisionHIL test suite.
"""

import os
import pytest


@pytest.fixture(autouse=True, scope="session")
def _cleanup_vision_debug():
    """Clean up the debug singleton camera after the entire test session."""
    yield
    if os.environ.get("VISION_DEBUG") == "1":
        from src.cv_validator import cleanup_debug

        cleanup_debug()
