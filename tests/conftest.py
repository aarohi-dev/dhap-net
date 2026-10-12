# tests/conftest.py
# Restore sys.stdout to the real stdout before pytest captures it.
# Some pipeline modules redirect sys.stdout to a UTF-8 TextIOWrapper at import time;
# this conftest undoes that so pytest's capture works correctly.

import sys
import io

def pytest_configure(config):
    """Restore stdout to a plain text-mode wrapper if it was replaced."""
    # If stdout was replaced with a custom TextIOWrapper wrapping buffer,
    # and pytest then closes it during teardown → ValueError.
    # Safe to reset to a fresh wrapper here before pytest sets up capturing.
    try:
        if hasattr(sys.stdout, 'buffer'):
            pass  # already has buffer; check encoding
        else:
            sys.stdout = io.TextIOWrapper(
                sys.__stdout__.buffer, encoding='utf-8', errors='replace'
            )
    except Exception:
        pass
    # Always reset to sys.__stdout__ which pytest can control
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
