"""Tests for CSV conversion."""

import shutil
from pathlib import Path

import pytest
from numbers_parser import Document


@pytest.mark.script_launch_mode("subprocess")
def test_help(script_runner) -> None:
    """Test conversion with no transforms."""
    ret = script_runner.run(["csv2numbers"], print_result=False)
    assert not ret.success
    assert "the following arguments are required" in ret.stderr

    ret = script_runner.run(["csv2numbers", "--help"], print_result=False)
    assert ret.success
    assert "usage: csv2numbers" in ret.stdout


@pytest.mark.script_launch_mode("subprocess")
def test_defaults(script_runner, tmp_path) -> None:
    """Test conversion with no transforms."""
    csv_path = str(tmp_path / "format-1.csv")
    shutil.copy("tests/data/format-1.csv", csv_path)

    ret = script_runner.run(["csv2numbers", csv_path], print_result=False)
    assert ret.stdout == ""
    assert ret.stderr == ""
    assert ret.success
    numbers_path = Path(csv_path).with_suffix(".numbers")

    assert numbers_path.exists()
    doc = Document(str(numbers_path))
    table = doc.sheets[0].tables[0]
    assert table.cell(3, 1).value == "GROCERY STORE        LONDON"
