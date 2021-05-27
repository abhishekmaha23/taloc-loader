import pandas as pd
import numpy as np
from cached_csv_from_xls import get_or_cache
from config import config
from trip_id import create_assign_trip

originals_folder = config['General']['originals_folder']


date_cols = ['flightDate']

col_mapping = {'departure': 'from', 'arrival': 'to',
               'pax': 'pax_count', 'travelClass': 'class',
               'flightNumber': 'flight_number', 'flightDate': 'leg_date',
               'flightReason': 'flight_reason',
               'flightReasonOther': 'flight_reason_other',
               'employeeName': 'pax_name', 'employeeID18': 'employee_id6',
               'employeeID19': 'employee_id8', 'FlightAmount': 'cost',
               'flightDateUnknown': 'leg_date_unknown', 'recordComments': 'comment',
               'provenience': 'provenience'
               }


import_cols = list(col_mapping)


def regular_legs_import(leg_files):
    spesen_csv_paths = [get_or_cache(f"{originals_folder}/{item}")
                        for item in leg_files]

    all_years = [pd.read_csv(path, dtype=str, parse_dates=date_cols, dayfirst=True, usecols=import_cols)
                 for path in spesen_csv_paths]

    spesen_nohr = pd.concat(all_years, axis=0)
    spesen_nohr.rename(columns=col_mapping, inplace=True)

    # Remove empty rows. XLS can keep rows with deleted content marked as active, but these shouldn't result
    # in additional leg records.
    spesen_nohr = spesen_nohr.loc[spesen_nohr['from'].notna(
    ) & spesen_nohr['to'].notna()]
    spesen_nohr.reset_index(inplace=True, drop=True)

    # read pax_count as a number (this is useful only later, _split_multi_pax)
    pd.to_numeric(spesen_nohr['pax_count'])
    # Convert leg_date_unknown to bool - interpret missing value as false.
    # Note how the leg date is populated because we know the trip start date and need to put that leg
    # somewhere in time to be able to analyze.
    # Note: All strings are truthy
    # https://stackoverflow.com/questions/52089711/why-is-astypebool-converting-all-values-to-true
    spesen_nohr['leg_date_unknown'] = spesen_nohr['leg_date_unknown'].fillna(
        'False').map({'False': False, 'True': True})

    # Error on unmapped strings (NaN is not an issue though)
    if spesen_nohr['leg_date_unknown'].dtype != 'bool':
        raise Exception(
            'Not all values in flightDateUnknown column were booleans')

    spesen_nohr['class'] = spesen_nohr['class'].str.upper()
    spesen_nohr['flight_number'] = spesen_nohr['flight_number'].str.upper()
    spesen_nohr['from'] = spesen_nohr['from'].str.upper()
    spesen_nohr['to'] = spesen_nohr['to'].str.upper()

    # Group trips by flightAmount aka cost, and employee_id8
    assign_trip = create_assign_trip(['cost', 'employee_id8'])
    spesen_nohr['trip_id'] = spesen_nohr.apply(
        lambda row: assign_trip(row), axis=1)

    # Label person type as employee or guest depending on whether there is a employee_id8
    spesen_nohr['employment'] = spesen_nohr.apply(lambda row: 'employee' if pd.notna(row['employee_id8']) or pd.notna(row['employee_id6']) else 'guest', axis=1)

    return spesen_nohr


def _remove_pax_cols(row):
    # Q: will dropping work and result in isna() on import?
    return row.drop(['employee_id6', 'employee_id8'])


# If we have > 1 pax, we consider the others - guests (internal/external unknown).
def _split_multi_pax(df):
    per_pax_list = []
    for _, row in df.iterrows():
        per_pax_list.append(row)
        i = row['pax_count'] - 1
        while i > 0:
            per_pax_list.append(_remove_pax_cols(row))
            i -= 1

    result = pd.DataFrame(per_pax_list)

    return result


###
# Change to one line per pax count, non-first lines have no name but keep the same demographics.
###
def expand_pax_count(spesen_legs, hr_data):
    df = pd.DataFrame.copy(spesen_legs)

    print('TODO: In _split_multi_pax, keep department of registered traveler.')

    per_pax = _split_multi_pax(df)

    return per_pax
