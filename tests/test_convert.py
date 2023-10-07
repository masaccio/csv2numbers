"""Tests for CSV conversion."""

import shutil
from pathlib import Path

from numbers_parser import Document
from pendulum import DateTime


def test_help(script_runner) -> None:
    """Test conversion with no transforms."""
    ret = script_runner.run(["csv2numbers"], print_result=False)
    assert not ret.success
    assert "the following arguments are required" in ret.stderr

    ret = script_runner.run(["csv2numbers", "--help"], print_result=False)
    assert ret.success
    assert "usage: csv2numbers" in ret.stdout


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


def test_errors(script_runner) -> None:
    """Test error detection in command line."""
    ret = script_runner.run(
        ["csv2numbers", "--delete=XX", "tests/data/format-1.csv"],
        print_result=False,
    )
    assert "XX: cannot delete: column not CSV file" in ret.stderr

    ret = script_runner.run(
        ["csv2numbers", "--transform=XX=POS:YY", "tests/data/format-1.csv"],
        print_result=False,
    )
    assert "merge failed: YY does not exist in CSV" in ret.stderr

    ret = script_runner.run(
        ["csv2numbers", "--transform=XX=FUNC:Account", "tests/data/format-1.csv"],
        print_result=False,
    )
    assert "FUNC: invalid transformation" in ret.stderr


def test_parse_error(script_runner) -> None:
    """Test conversion with no transforms."""
    ret = script_runner.run(
        ["csv2numbers", "tests/data/error.csv"],
        print_result=False,
    )
    assert "Error tokenizing data" in ret.stderr


def test_transforms(script_runner, tmp_path) -> None:
    """Test conversion with transformation."""
    csv_path = str(tmp_path / "format-2.csv")
    shutil.copy("tests/data/format-2.csv", csv_path)

    ret = script_runner.run(
        [
            "csv2numbers",
            "--whitespace",
            "--day-first",
            "--date=Date",
            "--transform=Paid In=POS:Amount",
            "--transform=Withdrawn=NEG:Amount",
            "--delete=Amount",
            "--delete=Balance",
            csv_path,
        ],
        print_result=False,
    )

    assert ret.stdout == ""
    assert ret.stderr == ""
    assert ret.success
    numbers_path = Path(csv_path).with_suffix(".numbers")

    assert numbers_path.exists()
    doc = Document(str(numbers_path))
    table = doc.sheets[0].tables[0]
    assert table.cell(3, 1).value == "JANE DOE GIFT CONTRIBUTION"
    assert str(table.cell(1, 0).value) == "2003-02-06T00:00:00+00:00"
    assert table.cell(0, 2).value == "Paid In"
    assert table.cell(0, 3).value == "Withdrawn"
    assert table.cell(3, 2).value == 10
    assert table.cell(4, 3).value == 20.4
