# Converter for CSV to Apple Numbers

[![build:](https://github.com/masaccio/csv2numbers/actions/workflows/run-all-tests.yml/badge.svg)](https://github.com/masaccio/csv2numbers/actions/workflows/run-all-tests.yml)
[![codecov](https://codecov.io/gh/masaccio/csv2numbers/branch/main/graph/badge.svg?token=EKIUFGT05E)](https://codecov.io/gh/masaccio/csv2numbers)
[![PyPI version](https://badge.fury.io/py/csv2numbers.svg)](https://badge.fury.io/py/csv2numbers)

`csv2numbers` is a command-line utility to convert CSV files to Apple Numbers spreadsheets.

## Installation

``` bash
python3 -m pip install csv2numbers
```

A pre-requisite for this package is [python-snappy](https://pypi.org/project/python-snappy/) which will be installed by Python automatically, but python-snappy also requires that the binary libraries for snappy compression are present.

The most straightforward way to install the binary dependencies is to use [Homebrew](https://brew.sh) and source Python from Homebrew rather than from macOS as described in the [python-snappy github](https://github.com/andrix/python-snappy):

For Intel Macs:

``` bash
brew install snappy python3
CPPFLAGS="-I/usr/local/include -L/usr/local/lib" python3 -m pip install python-snappy
```

For Apple Silicon Macs:

``` bash
brew install snappy python3
CPPFLAGS="-I/opt/homebrew/include -L/opt/homebrew/lib" python3 -m pip install python-snappy
```

For Linux (your package manager may be different):

``` bash
sudo apt-get -y install libsnappy-dev
```

On Windows, you will need to either arrange for snappy to be found for VSC++ or you can install python binary libraries compiled by [Christoph Gohlke](https://www.lfd.uci.edu/~gohlke/pythonlibs/#python-snappy). You must select the correct python version for your installation. For example for python 3.11:

``` text
C:\Users\Jon>pip install C:\Users\Jon\Downloads\python_snappy-0.6.1-cp311-cp311-win_amd64.whl
```

## Usage

Use `csv2numbers` to print command-line usage. You must provide at least one CSV file on the command-line and can provide multiple files, which will then all be converted using the same parameters. Output files can optionally be provided, but is none are provided, the output is created by replacing the input's files suffix with `.numbers`. For example:

``` text
csv2numbers file1.csv file2.csv -o file1.numbers file2.numbers
```

CSV files are read using the Excel dialect.

The following options affecting the output of the entire file. The default for each is always false.

* `--whitespace`: strip whitespace from beginning and end of strings and collapse other whitespace into single space
* `--reverse`: reverse the order of the data rows
* `--no-header`: CSV file has no header row
* `--day-first`: dates are represented day first in the CSV file

`csv2numbers` can also perform column manipulation. Columns can be identified using their name if the CSV file has a header or using a column index. Columns are zero-indexed and names and indices can be used together on the same command-line. When multiple columns are required, you can specify them using comma-separated values. The format for these arguments, like for the CSV file itself, the Excel dialect.

## Deleting columns

Delete columns using `--delete`. The names or indices of the columns to delete are specified as comma-separated values:

``` text
csv2numbers file1.csv --delete=Account,3
```

## Renaming columns

Rename columns using `--rename`. The current column name and new column name are separated by a `:` and each renaming is specified as comma-separated values:

``` text
csv2numbers file1.csv --rename=2:Account,"Paid In":Amount
```

## Date columns

The `--date` option identifies a comma-separated list of columns that should be parsed as dates. Use `--day-first` where the day and month is ambiguous anf the day comes first rather than the month.

## Transforming columns

Columns can be merged and new columns created using simple functions. The `--transform` option takes a comma-seperated list of transformations of the form `NEW:FUNC=OLD`. Supported functions are:

| Function    | Arguments | Description  |
| ----------- | --------- | ------------ |
| `MERGE`     | `dest=MERGE:source` | The `dest` column is writen with values from one or more columns indicated by `source`. For multiple columns, which are separated by `;`, the first empty value is chosen. |
| `NEG`       | `dest=NEG:source` | The `dest` column contains absolute values of any column that is negative. This is useful for isolating debits from account exports. |
| `POS`       | `dest=NEG:source` | The `dest` column contains values of any column that is positive. This is useful for isolating credits from account exports. |
| `LOOKUP`    | `dest=LOOKUP:source,filename` | A lookup map is read from `filename` which must be an Apple Numbers file containing a single table of two columns. The table is used to match agsinst `source`, searching the first column for matches and writing the corresponding value from the second column to `dest`. Values are chosen based on the longest matching substring. |

Examples:

``` text
csv2numbers --transform="Paid In"=POS:Amount,Withdrawn=NEG:Amount file1.csv
csv2numbers --transform=Category=LOOKUP:Transaction,mapping.numbers file1.csv
```

## License

All code in this repository is licensed under the [MIT License](https://github.com/masaccio/csv2numbers/blob/master/LICENSE.rst)
