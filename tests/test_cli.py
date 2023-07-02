import importlib.metadata

import pytest
from typer.testing import CliRunner

from macmoji.__main__ import app

runner = CliRunner()


@pytest.mark.parametrize("arg", ["--version", "-V"])
def test_version(arg):
    result = runner.invoke(app, arg)
    assert result.exit_code == 0
    assert f"MacMoji {importlib.metadata.version('macmoji')}" in result.stdout
