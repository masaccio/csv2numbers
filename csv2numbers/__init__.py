"""Convert a First Direct CSV export into a formatted Numbers document."""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from sys import exit, stderr
from typing import Tuple  # noqa: F401

import pandas as pd
from numbers_parser import Document


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
    if args.date is not None:
        parse_dates = [int(x) if x.isnumeric() else x for x in args.date]
    else:
        parse_dates = False
    try:
        data = pd.read_csv(
            args.csvfile,
            dayfirst=args.day_first,
            header=header,
            parse_dates=parse_dates,
        )
    except FileNotFoundError:
        fatal_error(f"{args.csvfile}: file not found")
    except pd.errors.ParserError as e:
        fatal_error(f"{args.csvfile}: {e.args[0]}")
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
    if map_strings is None:
        return data
    column_map = parse_column_map_strings(data, map_strings)
    return data.rename(columns=column_map)


def delete_columns(data: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Delete columns from the data."""
    if columns is None:
        return data

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


def col_names_for_transform(row: pd.Series, source: str, dest: str) -> tuple[str, str]:
    """Convert column name strings to pandas column names."""
    dest_col = int(dest) if dest.isnumeric() else dest
    source_cols = [int(x) if x.isnumeric() else x for x in source.split(",")]
    if not all(x in row for x in source_cols):
        fatal_error(f"merge failed: {source} does not exist in CSV")
    return (dest_col, source_cols)


def merge_row(row: pd.Series, source: str, dest: str) -> pd.Series:
    """Merge data in a single row."""
    (dest_col, source_cols) = col_names_for_transform(row, source, dest)
    value = ""
    for col in source_cols:
        if row[col] and not value:
            value = row[col]
    row[dest_col] = value
    return row


def merge_transform(data: pd.DataFrame, source: str, dest: str) -> pd.DataFrame:
    """Column transform to merge columns."""
    return data.apply(lambda row: merge_row(row, source, dest), axis=1)


def negative_values(row: pd.Series, source: str, dest: str) -> pd.Series:
    """Select negative values for a row."""
    (dest_col, source_cols) = col_names_for_transform(row, source, dest)
    value = ""
    for col in source_cols:
        if row[col] and not value and float(row[col]) < 0:
            value = abs(float(row[col]))
    row[dest_col] = value
    return row


def neg_transform(data: pd.DataFrame, source: str, dest: str) -> pd.DataFrame:
    """Column transform to select negative numbers."""
    return data.apply(lambda row: negative_values(row, source, dest), axis=1)


def positive_values(row: pd.Series, source: str, dest: str) -> pd.Series:
    """Select positive values for a row."""
    (dest_col, source_cols) = col_names_for_transform(row, source, dest)
    value = ""
    for col in source_cols:
        if row[col] and not value and float(row[col]) > 0:
            value = float(row[col])
    row[dest_col] = value
    return row


def pos_transform(data: pd.DataFrame, source: str, dest: str) -> pd.DataFrame:
    """Column transform to select positive numbers."""
    return data.apply(lambda row: positive_values(row, source, dest), axis=1)


def apply_transform(data: pd.DataFrame, transform: str) -> pd.DataFrame:
    """Transform columns with a function."""
    m = re.match(r"(.+)=(\w+):(.+)", transform)
    if not m:
        fatal_error(f"{transform}: invalid transformation format")
    dest = m.group(1)
    func = m.group(2).lower() + "_transform"
    source = m.group(3)
    if func not in globals():
        fatal_error(f"{m.group(2)}: invalid transformation")
    return globals()[func](data, source, dest)


def transform_data(data: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Perform any data transformations."""
    data = data.fillna("")
    for column in data.columns:
        if args.whitespace:
            data[column] = data[column].apply(func=filter_whitespace)
    if args.reverse:
        data = data.iloc[::-1]
        data = data.reset_index(drop=True)

    if args.transform is not None:
        for transform in args.transform:
            data = apply_transform(data, transform)

    return data


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
        "--delete",
        action="append",
        help="delete the named column; can be repeated",
    )
    parser.add_argument(
        "--date",
        action="append",
        help="parse the named column as a date; can be repeated",
    )
    parser.add_argument(
        "--rename",
        action="append",
        metavar="MAPPING",
        help="rename named column using the mapping format 'OLD:NEW'; can be repeated",
    )
    parser.add_argument(
        "--transform",
        action="append",
        metavar="MAPPING",
        help="transform values of columns into new columns; see docs for details",
    )
    parser.add_argument(
        "--output",
        metavar="FILENAME",
        help="output filename (default: use source file with .numbers)",
    )
    return parser.parse_args()


def main() -> None:
    """Convert the document and exit."""
    args = parse_command_line()

    data = read_csv_file(args)
    data = transform_data(data, args)
    data = rename_columns(data, args.rename)
    data = delete_columns(data, args.delete)

    if args.output is None:
        output_filename = Path(args.csvfile).with_suffix(".numbers")
    else:
        output_filename = args.output
    write_output(data, output_filename)


if __name__ == "__main__":
    main()
