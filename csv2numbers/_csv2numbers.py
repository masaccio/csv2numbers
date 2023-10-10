"""Command-line utility to convert CSV files to Apple Numbers spreadsheets."""
from __future__ import annotations

import argparse
import csv
import re
import warnings
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from sys import exit, stderr
from typing import NamedTuple, Tuple  # noqa: F401

import pandas as pd
from numbers_parser import Document, NumbersError

from csv2numbers import _get_version


def filter_whitespace(x: str) -> str:
    """Strip and collapse whitespace."""
    if isinstance(x, str):
        return re.sub(r"\s+", " ", x.strip())
    return x


class ColumnTransform(NamedTuple):
    """Class for holding a column transformation rule."""

    source: list[str]
    dest: str
    func: callable


@dataclass
class Converter:
    input_filename: str = None
    output_filename: str = None
    date_columns: list = None
    day_first: bool = False
    no_header: bool = False
    reverse: bool = False
    whitespace: bool = None

    def __post_init__(self: Converter) -> None:
        """Parse CSV file with Pandas and return a dataframe."""
        header = None if self.no_header else 0
        parse_dates = self.date_columns if self.date_columns is not None else False
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                self.data = pd.read_csv(
                    self.input_filename,
                    dayfirst=self.day_first,
                    header=header,
                    parse_dates=parse_dates,
                    thousands=",",
                )
        except FileNotFoundError as e:
            msg = f"{self.input_filename}: file not found"
            raise RuntimeError(msg) from e
        except pd.errors.ParserError as e:
            msg = f"{self.input_filename}: {e.args[0]}"
            raise RuntimeError(msg) from e
        else:
            self.data = self.data.fillna("")
            for column in self.data.columns:
                if self.whitespace:
                    self.data[column] = self.data[column].apply(func=filter_whitespace)

            if self.reverse:
                self.data = self.data.iloc[::-1]
                self.data = self.data.reset_index(drop=True)

    def rename_columns(self: Converter, mapper: dict) -> None:
        """Rename columns using column map."""
        if mapper is None:
            return
        self.data = self.data.rename(columns=mapper)

    def delete_columns(self: Converter, columns: list) -> None:
        """Delete columns from the data."""
        if columns is None:
            return

        try:
            index_to_name = dict(enumerate(self.data.columns))
            columns_to_delete = [
                index_to_name[x] if isinstance(x, int) else x for x in columns
            ]
            self.data = self.data.drop(columns=columns_to_delete)
        except KeyError:
            msg = "'" + "', '".join([str(x) for x in columns]) + "'"
            msg += ": cannot delete: column(s) do not exist in CSV"
            raise RuntimeError(msg) from None

    def transform_columns(self: Converter, columns: list[ColumnTransform]) -> None:
        """Perform column transformationstransformations."""
        if columns is None:
            return
        for transform in columns:
            self.data = transform.func(self.data, transform.source, transform.dest)

    def __del__(self: Converter) -> None:
        """Write dataframe transctions to a Numbers file."""
        doc = Document(num_rows=2, num_cols=2)
        table = doc.sheets[0].tables[0]

        for col_num, value in enumerate(self.data.columns.tolist()):
            table.write(0, col_num, value)

        for row_num, row in self.data.iterrows():
            for col_num, value in enumerate(row):
                if value:
                    table.write(row_num + 1, col_num, value)

        doc.save(self.output_filename)


def col_names_for_transform(row: pd.Series, source: str, dest: str) -> tuple[str, str]:
    """Convert column name strings to pandas column names."""
    dest_col = int(dest) if dest.isnumeric() else dest
    source_cols = [int(x) if x.isnumeric() else x for x in source.split(";")]
    if not all(x in row for x in source_cols):
        msg = f"merge failed: '{source}' does not exist in CSV"
        raise RuntimeError(msg)
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


def lookup_transform(data: pd.DataFrame, source: str, dest: str) -> pd.DataFrame:
    """Column trsnaform to map values based on a lookup table."""
    sources = source.split(";")
    if len(sources) != 2:
        msg = f"'{source}' LOOKUP must have exactly 2 arguments"
        raise RuntimeError(msg) from None

    (source, map_filname) = sources
    if not Path(map_filname).exists():
        msg = f"{map_filname}: no such file or directory"
        raise RuntimeError(msg) from None

    if source not in data.columns:
        msg = f"'{source}': column doesn't exist in CSV file"
        raise RuntimeError(msg) from None

    try:
        doc = Document(map_filname)
        table = doc.sheets[0].tables[0]
        lookup_map = {
            table.cell(row_num, 0).value: table.cell(row_num, 1).value
            for row_num in range(table.num_rows)
        }
    except NumbersError as e:
        msg = f"{map_filname}: {e!r}"
        raise RuntimeError(msg) from e
    else:
        matches_by_row = defaultdict(list)
        for key, value in lookup_map.items():
            row_ids = data[source][
                data[source].str.contains(key.lower(), case=False)
            ].index.tolist()
            for i in row_ids:
                matches_by_row[i].append({"value": value, "len": len(key)})
        data[dest] = ""
        for i, matches in matches_by_row.items():
            data.loc[i, dest] = max(matches, key=lambda x: x["len"])["value"]

    return data


def parse_columns(arg: str) -> list:
    """Parse a list of column names in Excel-compatible CSV format."""
    try:
        return [
            int(x) if x.isnumeric() else x for x in next(csv.reader([arg], strict=True))
        ]
    except csv.Error as e:
        msg = f"'{arg}': can't parse argument"
        raise argparse.ArgumentTypeError(msg) from e


def parse_column_renames(arg: str) -> dict:
    """Parse a list of column renames in Excel-compatible CSV format."""
    mapper = {}
    try:
        for mapping in next(csv.reader([arg], strict=True)):
            if mapping.count(":") != 1:
                msg = f"'{mapping}': column rename maps must be formatted 'OLD:NEW'"
                raise argparse.ArgumentTypeError(msg)
            (old, new) = mapping.split(":")
            old = int(old) if old.isnumeric() else old
            mapper[old] = new
    except csv.Error as e:
        msg = f"'{arg}': malformed CSV string"
        raise argparse.ArgumentTypeError(msg) from e
    else:
        return mapper


def parse_column_transforms(arg: str) -> list[ColumnTransform]:
    """Parse a list of column renames in Excel-compatible CSV format."""
    transforms = []
    try:
        for transform in next(csv.reader([arg], strict=True)):
            m = re.match(r"(.+)=(\w+):(.+)", transform)
            if not m:
                msg = f"'{transform}': invalid transformation format"
                raise argparse.ArgumentTypeError(msg)
            dest = m.group(1)
            func = m.group(2).lower() + "_transform"
            source = m.group(3)
            if func not in globals():
                msg = f"'{m.group(2)}': invalid transformation"
                raise argparse.ArgumentTypeError(msg)
            transforms.append(ColumnTransform(source, dest, globals()[func]))
    except csv.Error as e:
        msg = f"'{arg}': malformed CSV string"
        raise argparse.ArgumentTypeError(msg) from e
    else:
        return transforms


def command_line_parser() -> argparse.ArgumentParser:
    """Create a command-line argument parser and return parsed arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--version", action="store_true")
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
        "--date",
        metavar="COLUMNS",
        type=parse_columns,
        help="comma-separated list of column names/indexes to parse as dates",
    )
    parser.add_argument(
        "--rename",
        metavar="COLUMNS-MAP",
        type=parse_column_renames,
        help="comma-separated list of column names/indexes to renamed as 'OLD:NEW'",
    )
    parser.add_argument(
        "--transform",
        metavar="COLUMNS-MAP",
        type=parse_column_transforms,
        help="comma-separated list of column names/indexes to transform as 'NEW:FUNC=OLD'",
    )
    parser.add_argument(
        "--delete",
        metavar="COLUMNS",
        type=parse_columns,
        help="comma-separated list of column names/indexes to delete",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="*",
        metavar="FILENAME",
        help="output filename (default: use source file with .numbers)",
    )
    parser.add_argument("csvfile", nargs="*", help="CSV file to convert")
    return parser


def main() -> None:
    """Convert the document and exit."""
    parser = command_line_parser()
    args = parser.parse_args()

    if args.version:
        print(_get_version())
        exit(0)
    elif len(args.csvfile) == 0:
        print("At least one CSV file is required", file=stderr)
        parser.print_help(stderr)
        exit(1)

    if args.output is None:
        output_filenames = [Path(x).with_suffix(".numbers") for x in args.csvfile]
    else:
        output_filenames = args.output

    if len(args.csvfile) != len(output_filenames):
        print("The numbers of input and output file names do not match", file=stderr)
        exit(1)

    try:
        for input_filename, output_filename in zip(args.csvfile, output_filenames):
            converter = Converter(
                day_first=args.day_first,
                no_header=args.no_header,
                whitespace=args.whitespace,
                reverse=args.reverse,
                date_columns=args.date,
                input_filename=input_filename,
                output_filename=output_filename,
            )

            converter.transform_columns(args.transform)
            converter.rename_columns(args.rename)
            converter.delete_columns(args.delete)
    except RuntimeError as e:
        print(e, file=stderr)
        exit(1)


if __name__ == "__main__":  # pragma: no cover
    # execute only if run as a script
    main()
