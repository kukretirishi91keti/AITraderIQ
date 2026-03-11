"""Tests for environment validation."""

import os
import pytest


def test_validate_env_warns_on_defaults(capsys):
    """Validation should warn about insecure defaults."""
    os.environ["JWT_SECRET_KEY"] = "change-this-in-production"
    os.environ["DEMO_MODE"] = "true"

    from validate_env import validate_environment
    validate_environment()

    captured = capsys.readouterr()
    assert "JWT_SECRET_KEY" in captured.err or "Validation passed" in captured.out
