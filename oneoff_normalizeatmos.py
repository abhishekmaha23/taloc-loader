#######
# Normalize atmosfair response.
# This is part 2 of the oneoff_atmos exceptional process.
#
# After receiving atmosfair response:
# - You get the atmos report
# - I manually fill the extractor atmosfair cache with the returned data and don’t need an additional atmosfair send in this round (<1hr) I can also help to reconcile data if useful.
#   - remove person ID
#   - normalize to pax: 1
#   - how to deal with pax, charter, ..?
#
#######

import pandas as pd
import datetime as dt
from config import config
import re
from util import round_half_up

in_folder = 'data-originals/oneoff_normalizeatmos/'
out_folder = 'output'

# atmos delivered 2 files, xls and csv with differences
# 'xls' refers to the xls file we have manually opened, then saved as a csv
# This selects from which to normalize.
# But note results are always written to csv.
file_origin = 'csv'
atmosfair_filebase = {
    # 'xls': <xls-name>,
    'csv': 'atmosfair_CO2_Reporting_Flight_Uni.01.2017_31.12.2020_calculated-09.03.2021'
}

ROUNDING = 4
print('PLEASE CONFIRM ROUNDING OF 4')

# These are the column definitions and types we want left in the end.
# We are using the atmosfair convention and leaving that intact throughout this file.
flight_info = {'xls': ['Departure', 'Destination',
                       'Service class', 'Flight date', 'Flight number'],
               'csv': ['departure', 'arrival',
                       'travelClass', 'flightDate', 'flightNumber']}

# These are the columns that can be modified when we scale the pax count to 1.
scaled_results = {'xls': ['CO2 \n[t]', 'CO2 RFI2 [t]', 'CO2 RFI2.7 [t]', 'CO2 RFI4 [t]', 'CO2 DEFRA [t]',
                          'CO2 GHG/GRI [t]', 'CO2 ICAO [t]', 'CO2 VFU [t]', 'Total Distance [km]',
                          'Fuel use [tons kerosene]', 'Fuel use in critical altitudes [tons kerosene]', 'RFI 2 inkl. Kerosin-bereitstellung 15,2%'],
                  'csv': ['CO2', 'CO2RFI2', 'CO2RFI2.7', 'CO2RFI4', 'CO2DEFRA', 'CO2GHGGRI', 'CO2ICAO', 'CO2VFU', 'distance',
                          'fuel use', 'fuel use in critical altitudes']}

# We need to remove these cols from the dataset in order to de-duplicate it correctly.
dedupe_cols = {'xls': ['UniqueID atmosfair'], 'csv': ['UniqueID atmosfair']}

# And these can just be removed as we don't provide (and then expect back) them in future.
# 20210315: We drop "RFI 2 incl fuel provision 15.2% (t)" because it's calculated in excel and gets exported with a rounding error for either 4733 or 4897
# if we normalize - which is going to create duplicate records.
# We'll add that into the cache later (or even directly in cockpit)
delete_cols = {'xls': ['employeeName', 'provenience',
                       'RFI 2 inkl. Kerosin-bereitstellung 15,2%'],
               'csv': ['employeeName', 'provenience']}

# Note file convention for pax count. pax factor is min 1
pax_count = {'xls': 'Segments', 'csv': 'pax'}


# to divide GHG by pax count.
def scaledown(value, pax_count):
    return round_half_up(value / pax_count, ROUNDING) if pax_count > 1 else value


atmos_legs = pd.read_csv(f'{in_folder}/{atmosfair_filebase[file_origin]}.csv')

###
# Scale everything down to 1 pax
###
for result in scaled_results[file_origin]:
    atmos_legs[result] = atmos_legs.apply(lambda row: scaledown(
        row[result], row[pax_count[file_origin]]) if row[pax_count[file_origin]] > 1 else row[result], axis=1)
# Just to avoid any future misunderstanding.
atmos_legs[pax_count[file_origin]] = 1

###
# Take relevant columns only, de-duplicate
###
# atmos_legs = atmos_legs[fligRFI 2 inkl. Kerosin-bereitstellung 15,2%ht_info + unscaled_results[file_origin] + scaled_results[file_origin]]
# The delete_cols[file_origin] need to be dropped before de-duplicating the dataset.
atmos_legs.drop(columns=delete_cols[file_origin], inplace=True)
# There can only be duplicates once reducing to above column subset.
# atmos_legs.drop_duplicates(inplace=True)
# NOTE: Because we can't achieve perfectly same rounding in our own scaledown calculation
# as in atmosfair dataset, we cannot keep the results data in for de-duplication.
# (results may be slightly different, leading to additional rows which will blow up when
# we get to merging with any legs in the regular atmosfair.py).
atmos_legs.drop_duplicates(subset=flight_info[file_origin], inplace=True)

###
# Normalize date, write out file.
###
#
# atmos_legs['leg_date'] = atmos_legs['leg_date'].dt.strftime('%Y-%m-%d')
atmos_legs.to_csv(
    f'{out_folder}/{atmosfair_filebase[file_origin]}-normalized.csv', index=False)
quit()
