# Converter for CSV to Apple Numbers

[![build:](https://github.com/masaccio/csv2numbers/actions/workflows/run-all-tests.yml/badge.svg)](https://github.com/masaccio/csv2numbers/actions/workflows/run-all-tests.yml)
[![build:](https://github.com/masaccio/csv2numbers/actions/workflows/codeql.yml/badge.svg)](https://github.com/masaccio/csv2numbers/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/masaccio/csv2numbers/branch/main/graph/badge.svg?token=EKIUFGT05E)](https://codecov.io/gh/masaccio/csv2numbers)

`csv2numbers` is a command-line utility to convert CSV files to Apple Numbers spreadsheets.

## Usage

``` text
usage: csv2numbers [-h] [--whitespace] [--reverse] [--no-header]
[--day-first] [--delete DELETE] [--date DATE] [--rename MAPPING]
[--transform MAPPING] [--output FILENAME] csvfile

positional arguments:
  csvfile              CSV file to convert

options:
  -h, --help           show this help message and exit
  --whitespace         strip whitespace from beginning and end of strings and collapse
                       other whitespace into single space (default: false)
  --reverse            reverse the order of the data rows (default: false)
  --no-header          CSV file has no header row (default: false)
  --day-first          dates are represented day first in the CSV file (default: false)
  --delete DELETE      delete the named column; can be repeated
  --date DATE          parse the named column as a date; can be repeated
  --rename MAPPING     rename named column using the mapping format 'OLD:NEW'; can be repeated
  --transform MAPPING  transform values of columns into new columns; see docs for details
  --output FILENAME    output filename (default: use source file with .numbers)
```
