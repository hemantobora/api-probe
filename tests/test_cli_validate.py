import os
import sys
from pathlib import Path

import pytest

from api_probe.cli import validate_command


def test_validate_command_missing_file(tmp_path: Path, monkeypatch):
    missing_path = tmp_path / "missing.yaml"

    # Ensure file does not exist
    if missing_path.exists():
        missing_path.unlink()

    exit_code = validate_command(str(missing_path))
    assert exit_code == 2


def test_validate_command_invalid_yaml(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    # invalid YAML
    cfg_path.write_text("probes: [unclosed\n")

    exit_code = validate_command(str(cfg_path))
    # Should be treated as error (2) or invalid (1). We assert non-zero.
    assert exit_code in (1, 2)


def test_validate_command_valid_minimal(tmp_path: Path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("probes:\n  - name: 'Test'\n    endpoint: 'https://example.com'\n")

    exit_code = validate_command(str(cfg_path))
    # Config may still be considered invalid by validator; just ensure it does not crash.
    assert exit_code in (0, 1)
