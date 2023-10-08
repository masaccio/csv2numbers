"""Command-line utility to convert CSV files to Apple Numbers spreadsheets."""
import importlib.metadata

__version__ = importlib.metadata.version("csv2numbers")


def _get_version() -> str:
    return __version__
