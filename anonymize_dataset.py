import pandas as pd
from random import randrange
from datetime import timedelta
from functools import cache

# This is a placeholder function for now.
# Later, it'll have to work on the complete dataset including GHG and HR data.
lookup = {
    'count': 1
}

# Anonymize name -> PaxNN, but same name -> same PaxNN


def anon_name(name):
    if not name in lookup:
        lookup[name] = 'Pax{}'.format(lookup['count'])
        lookup['count'] += 1
    return lookup[name]


def anonymize_dataset(orig_df):
    df = pd.DataFrame.copy(orig_df)
    df['pax_name'] = df.apply(lambda row: anon_name(row['pax_name']), axis=1)
    # 1 less because of 'count'
    print('number of different Pax:', len(lookup) - 1)
    return df


# Generate arbitrary day offset per trip but same for all legs of a trip.
@cache
def _get_offset(trip_id):
    while True:
        # We're moving into future only to avoid
        # 2016 records which would look strange.
        rnd = randrange(0, 15)
        if rnd != 0:
            break
    return rnd


def _date_offset(row):
    offset = _get_offset(row['trip_id'])

    # datetime representation
    leg_date = pd.to_datetime(row['leg_date'])
    # add offset
    # leg_date += timedelta(days=_date_offset_lookup[key])
    leg_date += timedelta(days=offset)

    # back to string
    str_date = leg_date.strftime('%Y-%m-%d')

    return str_date


def move_dates(orig_df):
    df = pd.DataFrame.copy(orig_df)
    df['leg_date'] = df.apply(lambda row: _date_offset(row), axis=1)
    return df
