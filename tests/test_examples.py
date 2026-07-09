"""Smoke test: every script in examples/ runs via the literal command a
newcomer types (`python examples/<name>.py --smoke`)."""
import pathlib
import subprocess
import sys

import pytest

EXAMPLES = sorted((pathlib.Path(__file__).parent.parent / "examples").glob("*.py"))


@pytest.mark.parametrize("script", EXAMPLES, ids=lambda p: p.name)
def test_example_smoke(script):
    result = subprocess.run([sys.executable, str(script), "--smoke"],
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr
