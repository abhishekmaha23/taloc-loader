# XLS parsing is super slow.
# So given a name, first check if the csv is available, else create a csv "cache"
# for the provided xls, and return the file handle to it.
# We are not directly loading it here because the caller might want to provide
# custom options.
import pandas as pd
import os.path
import pathlib
import re

cached_data_dir = 'data-cached'


def cached_csv_from_xls(xls_path, sheet_name):
    filename = os.path.basename(xls_path)
    basename = os.path.splitext(filename)[0]
    # dirname = os.path.dirname(xls_path)

    csv_name = f"{basename}-{sheet_name}.csv"

    cached_csv_path = f"{cached_data_dir}/{csv_name}"

    # If the corresponding csv does not exist, create it
    if not os.path.isfile(cached_csv_path):
        # na_filter prevents the department NULL to be read as NaN.
        data_xls = pd.read_excel(xls_path, sheet_name, index_col=None, dtype=str, na_filter=False)
        data_xls.to_csv(cached_csv_path, encoding='utf-8', index=False)

    return cached_csv_path


# Check if name ends with csv..
def is_csv(path):
    # xls+sheet name notation.
    if '[' in path:
        return False

    return os.path.splitext(path)[1].casefold() == '.csv'


# This is our "excel + sheet" convention
matcher = re.compile(r'(.*)\[(.*)\](.*)')
# sheet_names can optionally be indicated for our paths.


def parse_xls_path(path):
    if '[' not in path:
        # Default to MS default which is Sheet1
        return [path, 'Sheet1']

    m = matcher.match(path)

    return [f"{m.group(1)}{m.group(2)}", m.group(3)]


# If we provide an excel path, create a cached csv and return its path.
# We can also use a notation to indicate sheet names: 'path/to/[name.xlsx]sheet name'
# If we provide an csv path: just return it
def get_or_cache(path):
    if (is_csv(path)):
        return path
    [xls_path, sheet_name] = parse_xls_path(path)

    # Quality check.
    if not '.xls' in os.path.splitext(path)[1].casefold():
        raise Exception(f"Unsupported: Neither csv nor xls(x): {path}")

    return cached_csv_from_xls(xls_path, sheet_name)
