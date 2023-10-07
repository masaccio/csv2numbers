"""Convert a First Direct CSV export into a formatted Numbers document."""

import argparse
import re
from pathlib import Path
from sys import exit, stderr

import pandas as pd
from numbers_parser import Document

CSV_SAMPLE_LENGTH = 8192


def filter_positive(x: str) -> str:
    """Return positive values or None."""
    value = float(x)
    return None if value < 0.0 else value


def filter_negative(x: str) -> str:
    """Return absolute values if less than zero or None."""
    value = float(x)
    return None if value > 0.0 else abs(value)


def filter_whitespace(x: str) -> str:
    """Strip and collapse whitespace."""
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x.strip())
    return x


def write_output(data: pd.DataFrame, filename: str) -> None:
    """Write dataframe transctions to a Numbers file."""
    doc = Document(num_rows=2, num_cols=2)
    table = doc.sheets[0].tables[0]

    for col_num, value in enumerate(data.columns.tolist()):
        table.write(0, col_num, value)

    for row_num, row in data.iterrows():
        for col_num, value in enumerate(row):
            if value:
                table.write(row_num + 1, col_num, value)

    doc.save(filename)


def read_csv_file(args: argparse.Namespace) -> pd.DataFrame:
    """Parse CSV file with Pandas and return a dataframe."""
    header = None if args.no_header else 0
    try:
        data = pd.read_csv(
            args.csvfile,
            header=header,
            parse_dates=True,
            dayfirst=args.day_first,
        )
    except FileNotFoundError:
        fatal_error(f"{args.csvfile}: file not found")
    return data


def fatal_error(error: str) -> None:
    """Print a fatal error message and exit."""
    print(error, file=stderr)
    exit(1)


def parse_column_map_strings(data: pd.DataFrame, map_strings: list) -> dict:
    """Parse and validate a list of column mappings and return as a dict."""
    mapping = {}
    try:
        for map_string in map_strings:
            (k, v) = map_string.split(":")
            if not k or not v:
                fatal_error(f"{map_string}: invalid column rename format")
            if k.isnumeric():
                k = int(k)
            if k not in data.columns:
                fatal_error(f"{k}: column does not exist")
            mapping[k] = v
    except ValueError:
        fatal_error(f"{map_string}: invalid column rename format")
    return mapping


def rename_columns(data: pd.DataFrame, map_strings: list) -> pd.DataFrame:
    """Rename columns using column map."""
    column_map = parse_column_map_strings(data, map_strings)
    return data.rename(columns=column_map)


def delete_columns(data: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Delete columns from the data."""
    columns_to_delete = []
    for column in columns:
        if column.isnumeric():
            if int(column) not in data.columns:
                fatal_error(f"{column}: cannot delete: column not CSV file")
            columns_to_delete.append(int(column))
        elif column not in data.columns:
            fatal_error(f"{column}: cannot delete: column not CSV file")
        else:
            columns_to_delete.append(column)

    if len(columns_to_delete) > 0:
        return data.drop(columns=columns_to_delete)
    return data


def transform_rows(data: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Remove whitespace and re-order if required."""
    for column in data.columns:
        if args.whitespace:
            data[column] = data[column].apply(func=filter_whitespace)
    if args.reverse:
        data = data.iloc[::-1]
        data = data.reset_index(drop=True)

    return data.fillna("")


def parse_command_line() -> argparse.Namespace:
    """Create a command-line argument parser and return parsed arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("csvfile", help="CSV file to convert")
    parser.add_argument(
        "--whitespace",
        required=False,
        action="store_true",
        help="strip whitespace from beginning and end of strings and "
        "collapse other whitespace into single space (default: false)",
    )
    parser.add_argument(
        "--reverse",
        required=False,
        action="store_true",
        help="reverse the order of the data rows (default: false)",
    )
    parser.add_argument(
        "--no-header",
        required=False,
        action="store_true",
        help="CSV file has no header row (default: false)",
    )
    parser.add_argument(
        "--day-first",
        required=False,
        action="store_true",
        help="dates are represented day first in the CSV file (default: false)",
    )
    parser.add_argument(
        "--delete-column",
        action="append",
        help="delete the named column; can be repeated",
    )
    parser.add_argument(
        "--rename-column",
        action="append",
        metavar="MAPPING",
        help="rename named column using the mapping format 'OLD:NEW'; can be repeated",
    )
    parser.add_argument(
        "--transform-column",
        action="append",
        metavar="MAPPING",
        help="transform values of columns into new columns; see docs for details",
    )
    return parser.parse_args()


def main() -> None:
    """Convert the document and exit."""
    args = parse_command_line()

    data = read_csv_file(args)
    data = rename_columns(data, args.rename_column)
    data = delete_columns(data, args.delete_column)
    data = transform_rows(data, args)

    print(data)

    numbers_filename = Path(args.csvfile).with_suffix(".numbers")
    write_output(data, numbers_filename)


if __name__ == "__main__":
    main()
