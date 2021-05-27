####
# upfront:
# 1. read cache.
#
# Runtime:
# 1. For every leg, try to associate cached atmosfair data
# 2. Assemble a list of legs where this is not possible.
# 3. add list of records with no cache to output/.
####
from config import config
import pandas as pd
from excel_writer_formatted import to_excel
import re
import os.path
import glob
from datetime import datetime
from util import file_timestamp

# Build the cache from the atmosfair xls responses or csv responses.
# We started out by using xls and then moved to csv.
file_origin = 'csv'

print('TODO: Warn on atmosfair response "INT-INT" and handle Aircraft = "Train"')

originals_path = config['General']['originals_folder']
output_folder = config['General']['output_folder']
atmosfair_responses_folder = config['atmosfair']['responses_folder']

atmos_responses_path = f"{originals_path}/{atmosfair_responses_folder}"
all_atmos_response_files = glob.glob(
    os.path.join(atmos_responses_path, "*.csv"))


atmos_date_col = {'xls': 'Flight date', 'csv': 'flightDate'}

####
# The reason for this indirection is that currently we use these labels directly inside the cockpit,
# and there have been requests to change the labels which for now we do here.
# With the atmos_def dict we change all instances in the same location, here.
####
atmos_def = {
    'co2': 'CO2e (t)',
    'co2rfi2': 'CO2e RFI2 (t)',
    'co2rfi2.7': 'CO2e RFI2.7 (t)',
    'co2rfi4': 'CO2e RFI4 (t)',
    'co2defra': 'CO2e DEFRA (t)',
    'co2ghggri': 'CO2e GHG/GRI (t)',
    'co2icao': 'CO2e ICAO (t)',
    'co2rfi2': 'CO2e RFI2 (t)',
    'co2vfu': 'CO2e VFU (t)',
    'distance': 'Total Distance (km)',
    'specificfuel': 'Specific fuel consumption (l)',
    'cruisealt': 'Cruise altitude (m)',
    'fueluse': 'Kerosene use (t)',
    'fuelusecritalt': 'Kerosene use in critical altitudes (t)',
    'fuelsharecruise': 'Share of fuel use in cruise (%)'
}

atmos_mapping = {
    'xls': {
        # Below are unused for now
        'Activity': 'Activity',
        'charter': 'charter',
        'UniqueID atmosfair': 'UniqueID atmosfair',
        # Used: from here on
        'Departure': 'from',
        'Destination': 'to',
        'Segments': 'pax_count',
        'Service class': 'class',
        'Flight number': 'flight_number',
        atmos_date_col[file_origin]: 'leg_date',
        'Aircraft type': 'aircraft_type',
        # Fixing that newline, too.
        'CO2 \n[t]': atmos_def['co2'],
        'CO2 RFI2 [t]': atmos_def['co2rfi2'],
        'CO2 RFI2.7 [t]': atmos_def['co2rfi2.7'],
        'CO2 RFI4 [t]': atmos_def['co2rfi4'],
        'CO2 DEFRA [t]': atmos_def['co2defra'],
        'CO2 GHG/GRI [t]': atmos_def['co2ghggri'],
        'CO2 ICAO [t]': atmos_def['co2icao'],
        'CO2 VFU [t]': atmos_def['co2vfu'],
        'Total Distance [km]': atmos_def['distance'],
        'Specific fuel consumption [liter]': atmos_def['specificfuel'],
        'Cruise altitude [m]': atmos_def['cruisealt'],
        'Fuel use [tons kerosene]': atmos_def['fueluse'],
        'Fuel use in critical altitudes [tons kerosene]': atmos_def['fuelusecritalt'],
        'Share of fuel use in cruise [%]': atmos_def['fuelsharecruise'],
        # We don't import this one, see also oneoff_atmos comments. Calculated per atmos formula instead
        # 'RFI 2 inkl. Kerosin-bereitstellung 15,2%': 'RFI 2 incl fuel provision 15.2% (t)'
    },
    'csv': {
        # Below are unused for now
        # csv has no 'Activity'
        # 'Activity': 'Activity',
        'charter': 'charter',
        'UniqueID atmosfair': 'UniqueID atmosfair',
        # Used: from here on
        'departure': 'from',
        'arrival': 'to',
        'pax': 'pax_count',
        'travelClass': 'class',
        'flightNumber': 'flight_number',
        atmos_date_col[file_origin]: 'leg_date',
        'aircraft': 'aircraft_type',
        # Fixing that newline, too.
        'CO2': atmos_def['co2'],
        'CO2RFI2': atmos_def['co2rfi2'],
        'CO2RFI2.7': atmos_def['co2rfi2.7'],
        'CO2RFI4': atmos_def['co2rfi4'],
        'CO2DEFRA': atmos_def['co2defra'],
        'CO2GHGGRI': atmos_def['co2ghggri'],
        'CO2ICAO': atmos_def['co2icao'],
        'CO2VFU': atmos_def['co2vfu'],
        'distance': atmos_def['distance'],
        'specific fuel consumption': atmos_def['specificfuel'],
        'cruise altitude': atmos_def['cruisealt'],
        'fuel use': atmos_def['fueluse'],
        'fuel use in critical altitudes': atmos_def['fuelusecritalt'],
        'share of fuel use in cruise': atmos_def['fuelsharecruise'],
        # Note csv has no "RFI2 + Bereitstellung 15.2%" column.
        # But today we're ignoring "method" and "flight" (latter are calc comments)
    }}

raw_floats = {'xls': ['CO2 \n[t]',
                      'CO2 RFI2 [t]',
                      'CO2 RFI2.7 [t]',
                      'CO2 RFI4 [t]',
                      'CO2 DEFRA [t]',
                      'CO2 GHG/GRI [t]',
                      'CO2 ICAO [t]',
                      'CO2 VFU [t]',
                      'Total Distance [km]',
                      'Specific fuel consumption [liter]',
                      'Cruise altitude [m]',
                      'Fuel use [tons kerosene]',
                      'Fuel use in critical altitudes [tons kerosene]'],
              'csv': ['CO2',
                      'CO2RFI2',
                      'CO2RFI2.7',
                      'CO2RFI4',
                      'CO2DEFRA',
                      'CO2GHGGRI',
                      'CO2ICAO',
                      'CO2VFU',
                      'distance',
                      'specific fuel consumption',
                      'cruise altitude',
                      'fuel use',
                      'fuel use in critical altitudes']}


atmos_inv_mapping = {v: k for k, v in atmos_mapping[file_origin].items()}

# The unique keys describing the flight
q_keys = ['from', 'to', 'class', 'leg_date', 'flight_number']

drop_keys = {'xls': ['Activity', 'charter', 'UniqueID atmosfair', 'pax_count'],
             'csv': ['charter', 'UniqueID atmosfair', 'pax_count']}
# Everything we do not remove.
keep_keys = list(set(list(atmos_inv_mapping)) - set(drop_keys[file_origin]))

# We assume we're missing results if this col is not defined.
# We'd normally use the plain `CO2` but that one has mis-formatted column header in atmosfair shipment 1.
result_sample_key = atmos_def['co2rfi2']

atmosfair_cache = None

# We have 2 columns identically named 'aircraft' and atmosfair ensures us that the second one is populated
# by them. The first one apparently is the one sent by us to them per their data specs, which is empty though.
# This function naming the one by atmosfair 'aircraft'. It also handles the possibility that we only get their aircraft column,
# in which case no change is required.


def fix_duplicate_aircraft_col(df):
    if 'aircraft.1' in df.columns:
        if not 'aircraft' in df.columns:
            raise Exception(
                'This counters the assumption that `aircraft.1` col exists as a duplicate `aircraft` col.')

        if len(df[df['aircraft'].notna()]) > 0:
            raise Exception(
                'Failed to remove surplus `aircraft` column: not all rows are undefined')

        # Drop the useless aircraft column (it's further left and therefore keeps the name)
        df.drop(columns=['aircraft'], inplace=True)
        df.rename(columns={'aircraft.1': 'aircraft'}, inplace=True)
    return df


# Build atmosfair_cache from csv files at startup.
if len(all_atmos_response_files):
    atmosfair_cache = pd.concat(fix_duplicate_aircraft_col(
        pd.read_csv(f, dtype=str)) for f in all_atmos_response_files)

    # Fix that Unnamed: 11 column which sometimes occurs in atmosfair shipments and doesn't mean anything.
    # (Minor. Reason: they say we shipped it - could check if our shipments to them end the line with a comma)
    if 'Unnamed: 11' in atmosfair_cache.columns:
        atmosfair_cache.drop(columns='Unnamed: 11', inplace=True)

    atmosfair_cache = atmosfair_cache.astype(
        {v: float for v in raw_floats[file_origin]})
    # Be extra careful about day order of dates for parsing, since that has changed back and forth during the project.
    # Standardize the internal represenation of dates as iso.
    sample_date = atmosfair_cache.iloc[0][atmos_date_col[file_origin]]
    if re.match(r'^[0-9]{2}\.[0-9]{2}\.20[0-9]{2}', sample_date):
        atmosfair_cache[atmos_date_col[file_origin]] = pd.to_datetime(
            atmosfair_cache[atmos_date_col[file_origin]], dayfirst=True).dt.strftime('%Y-%m-%d')
    else:
        raise Exception('Double-check date format of atmosfair cache!')

    atmosfair_cache.rename(columns=atmos_mapping[file_origin], inplace=True)

    # Importantly, drop pax_count which we expect to always be ==1. Otherwise, this could get confused when merging cache with real legs.
    for drop_key in drop_keys[file_origin]:
        if drop_key in atmosfair_cache.columns:
            atmosfair_cache.drop(columns=[drop_key], inplace=True)

    # fillna('') is to ensure correct merging, see below
    atmosfair_cache.fillna('', inplace=True)
    # Finally, create correct format.
else:
    atmosfair_cache = pd.DataFrame(columns=keep_keys)


def _to_atmosfair_format(df):
    atmos = pd.DataFrame.copy(df)
    atmos.rename(columns=atmos_inv_mapping, inplace=True)
    # Atmosfair may prefer dd.mm.yyyy format (iso unconfirmed).
    atmos[atmos_date_col[file_origin]] = pd.to_datetime(
        atmos[atmos_date_col[file_origin]]).dt.strftime('%d.%m.%Y')

    # Arbitrary stuff that may help atmosfair
    atmos['pax'] = '1'
    atmos['aircraft'] = ''
    atmos['charter'] = ''
    return atmos


# NOTE: This merges atmosfair GHG data but does not consider pax_count > 1.
# The latter has to be adjusted in a separate step.
def merge_emissions(raw_legs_df):
    legs = pd.DataFrame.copy(raw_legs_df)

    # The merge is not predictable on nan keys:
    # https://stackoverflow.com/questions/53688988/why-does-pandas-merge-on-nan
    # Therefore, create predictable keys.
    # This will convert nat to nan
    legs['leg_date'] = legs['leg_date'].dt.strftime('%Y-%m-%d')
    # And now that everything undefined is nan, we can fill
    legs.fillna('', inplace=True)

    with_cache = pd.merge(legs, atmosfair_cache, how='left', on=q_keys)

    missing = with_cache[with_cache[result_sample_key].isna()
                         ][q_keys]

    miss_count = missing.shape[0]
    catch_hits = with_cache.shape[0] - miss_count

    print(f"Info: atmosfair cache hits: {catch_hits} of {legs.shape[0]}.", end=" ")
    print(
        f"Total legs including \"pax count > 1\" entries: {with_cache['pax_count'].astype('int').sum()}")
    ghg_request_filepath = None

    if miss_count > 0:
        # We only need/want one record per unique flight, to add to the cache
        missing = missing[missing.duplicated(q_keys) == False]

        ghg_request_filepath = f"{output_folder}/to_atmosfair_{file_timestamp()}.csv"

        atmos_transfer = _to_atmosfair_format(missing)

        atmos_transfer.to_csv(ghg_request_filepath, index=False)
        # If we wanted an excel for users.
        # to_excel(atmos_transfer, f"{output_folder}/{filename}", index=False)

    return [with_cache, ghg_request_filepath]
