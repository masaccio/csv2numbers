"""Tests for CSV conversion."""

import shutil
from pathlib import Path

import pytest
from numbers_parser import Document

from csv2numbers import _get_version


def test_help(script_runner) -> None:
    """Test conversion with no transforms."""
    ret = script_runner.run(["csv2numbers"], print_result=False)
    assert not ret.success
    assert "At least one CSV file is required" in ret.stderr

    ret = script_runner.run(["csv2numbers", "--help"], print_result=False)
    assert ret.success
    assert "usage: csv2numbers" in ret.stdout


@pytest.mark.script_launch_mode("subprocess")
def test_version(script_runner) -> None:
    """Test Version number."""
    ret = script_runner.run(["csv2numbers", "-V"], print_result=False)
    assert ret.stderr == ""
    assert ret.stdout.strip() == _get_version()

    ret = script_runner.run(["python3", "-m", "csv2numbers", "-V"], print_result=False)
    assert ret.stderr == ""
    assert ret.stdout.strip() == _get_version()


def test_defaults(script_runner, tmp_path) -> None:
    """Test conversion with no options."""
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


@pytest.mark.script_launch_mode("subprocess")
def test_errors(script_runner) -> None:
    """Test error detection in command line."""
    ret = script_runner.run(
        ["csv2numbers", "--delete=XX", "tests/data/format-1.csv"],
        print_result=False,
    )
    assert "'XX': cannot delete" in ret.stderr

    ret = script_runner.run(
        ["csv2numbers", "--transform=XX=POS:YY", "tests/data/format-1.csv"],
        print_result=False,
    )
    assert "merge failed: YY does not exist in CSV" in ret.stderr

    ret = script_runner.run(
        ["csv2numbers", "--transform=XX=FUNC:Account", "tests/data/format-1.csv"],
        print_result=False,
    )
    assert "'FUNC': invalid transformation" in ret.stderr


@pytest.mark.script_launch_mode("subprocess")
def test_parse_error(script_runner) -> None:
    """Test conversion with no transforms."""
    ret = script_runner.run(
        ["csv2numbers", "tests/data/error.csv"],
        print_result=False,
    )
    assert "Error tokenizing data" in ret.stderr


def test_transforms_format_1(script_runner, tmp_path) -> None:
    """Test conversion with transformation."""
    csv_path = str(tmp_path / "format-1.csv")
    shutil.copy("tests/data/format-1.csv", csv_path)

    ret = script_runner.run(
        [
            "csv2numbers",
            "--whitespace",
            "--day-first",
            "--date=Date",
            "--delete=Card Member,Account #",
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
    assert table.cell(1, 1).value == "GROCERY STORE LONDON"
    assert str(table.cell(2, 0).value) == "2008-04-05T00:00:00+00:00"
    assert table.cell(6, 2).value == 4.99


def test_transforms_format_2(script_runner, tmp_path) -> None:
    """Test conversion with transformation."""
    csv_path = str(tmp_path / "format-2.csv")
    shutil.copy("tests/data/format-2.csv", csv_path)

    ret = script_runner.run(
        [
            "csv2numbers",
            "--whitespace",
            "--day-first",
            "--date=Date",
            "--transform=Paid In=POS:Amount,Withdrawn=NEG:Amount",
            "--delete=Amount,Balance",
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
    assert table.cell(0, 2).value == "Paid In"
    assert table.cell(0, 3).value == "Withdrawn"
    assert table.cell(1, 3).value == 1.4
    assert table.cell(3, 2).value == 10.0
    assert str(table.cell(3, 0).value) == "2003-02-04T00:00:00+00:00"


def test_transforms_format_3(script_runner, tmp_path) -> None:
    """Test conversion with transformation."""
    csv_path = str(tmp_path / "format-3.csv")
    shutil.copy("tests/data/format-3.csv", csv_path)

    ret = script_runner.run(
        [
            "csv2numbers",
            "--delete=2,3,4,5",
            "--date=0",
            "--day-first",
            "--no-header",
            "--rename=0:Date,1:Transaction,6:Amount",
            "--transform=6=MERGE:5;6",
            "--whitespace",
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
    assert table.cell(5, 1).value == "AutoShop.com"
    assert str(table.cell(7, 0).value) == "2023-09-26T00:00:00+00:00"
    assert table.cell(0, 1).value == "Transaction"
    assert table.cell(0, 2).value == "Amount"
    assert table.cell(7, 2).value == -1283.72
