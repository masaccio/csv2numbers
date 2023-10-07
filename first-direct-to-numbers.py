"""Convert a First Direct CSV export into a formatted Numbers document."""

from argparse import ArgumentParser
from pathlib import Path
from sys import exit, stderr

import pandas as pd
from numbers_parser import Document


def paid_in_amount(x: str) -> str:
    """Filter positive values paid in."""
    value = float(x)
    return None if value < 0.0 else value


def withdrawn_amount(x: str) -> str:
    """Filter negative values withdrawn."""
    value = float(x)
    return None if value > 0.0 else -value


def write_output(transactions: pd.DataFrame, filename: str) -> None:
    """Write dataframe transctions to a Numbers file."""
    doc = Document(num_rows=2, num_cols=2)
    table = doc.sheets[0].tables[0]

    for col_num, value in enumerate(transactions.columns.tolist()):
        table.write(0, col_num, value)

    for row_num, row in transactions.iterrows():
        for col_num, value in enumerate(row):
            if value:
                table.write(row_num + 1, col_num, value)

    doc.save(filename)


def main() -> int:
    """Convert the document and exit."""
    parser = ArgumentParser()
    parser.add_argument("csvfile", help="CSV exported from account")
    args = parser.parse_args()

    try:
        transactions = pd.read_csv(args.csvfile, parse_dates=["Date"], dayfirst=True)
    except FileNotFoundError:
        print(f"{args.csvfile}: file not found", file=stderr)
        return 1

    transactions.Description = transactions.Description.replace(r"\s+", " ", regex=True)
    transactions["Paid In"] = transactions.Amount.apply(func=paid_in_amount)
    transactions["Withdrawn"] = transactions.Amount.apply(func=withdrawn_amount)
    transactions = transactions.drop(columns=["Amount", "Balance"])
    transactions = transactions.iloc[::-1]
    transactions = transactions.fillna("")
    transactions = transactions.reset_index(drop=True)

    numbers_filename = Path(args.csvfile).with_suffix(".numbers")
    write_output(transactions, numbers_filename)
    return 0


if __name__ == "__main__":
    exit(main())
