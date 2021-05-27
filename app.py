import pandas as pd
import datetime as dt
from atmosfair_test import atmosfair_test
from anonymize_dataset import anonymize_dataset, move_dates
from airports import get_legs_airport_data
from hr import assign_employee_id8, find_hr_matches, hr_bta_fill_instructions, \
    demographics_by_year, merge_demographics, get_org_fte, hr_issues
from bta_legs_import import bta_legs_import
from regular_legs_import import regular_legs_import
from config import config
from atmosfair import merge_emissions, atmos_def
from expand_pax_counts import expand_pax_counts
from trip_date import exclude_newer
from format_legs import compact_dict, write_json
from excel_writer_formatted import to_excel
from util import file_timestamp

# Collect all the items the user will have to work on to complete and/or clean the data.
user_todos = []

# We can have multiple types of hr issues. Starting the collecting of all of them here.
hr_issue_list = pd.DataFrame.copy(hr_issues)

# The files named oneoff_* have been used once for initial process exceptions.
# For now they should be dragged along, in case we ever have a similar situation.
# This import would create a large collective file and a pseudonymization file
# import oneoff_atmos
# import oneoff_normalizeatmos
# quit()

originals_folder = config['General']['originals_folder']
output_folder = config['General']['output_folder']

print('TODO: Ensure atmos transfers are either older than 6 months or repeated. Also a process question, when does extract happen.')
# Simple answer: don't send younger than 6 months. Complicated: Replace records younger than 6 months at time of atmos request.
print('TODO: indicate process for loading a datafile from datahub and extending it. Indicate fields to be completed.')

print('TODO: data-cached gave a big speed-up but is also potentially dangerous. Disable or add file hash or similar')

####
# Load all air travel data (1 flight segment per row)
# First bta since it needs special treatment, then the others and combine.
####

# Load bta data first. Later, assign employee ids by way of matching traveler names to HR records.
# After the matching, bta data will have the same shape as other air leg imports.
bta_legs_noid8 = bta_legs_import()

# vvvv MATCH bta pax names get employee id8
[bta_id8_map, marked_missing,
    name_matches_request] = find_hr_matches(bta_legs_noid8)

if marked_missing and len(marked_missing):
    hr_issue_list_add1 = pd.DataFrame()
    hr_issue_list_add1['pax_name'] = marked_missing
    hr_issue_list_add1['comment'] = 'Marked as NR in hr_bta_matches, please add a person with matching name to HR excerpts.'

    hr_issue_list = pd.concat(
        [hr_issue_list, hr_issue_list_add1], axis=0)


if name_matches_request:
    user_todos.append(
        f"Please fill the matches column in {name_matches_request['output']}, save the result to the {name_matches_request['input']}/ folder" +
        hr_bta_fill_instructions
    )


# Finalize legs by assigning correct personal information.
# Note that non-bta legs have both id6 and id8 employee ids, and bta legs only have id8
# Not an issue since we don't care about old id6.
bta_legs_nohr = assign_employee_id8(
    bta_legs_noid8, bta_id8_map, marked_missing)
# ^^^^ MATCH bta pax names get employee id8

# vvvv Load all legs
spesen_legs_nohr = regular_legs_import(config['legs']['spesen'])
airplus_legs_nohr = regular_legs_import(config['legs']['airplus'])

# Combine all legs
all_legs_nohr = pd.concat(
    [bta_legs_nohr, spesen_legs_nohr, airplus_legs_nohr], axis=0)
# ^^^^Load all legs

####
# Now that we have all flight segments, add the emission data.
# Emission data previously received are cached in a file, so when we
# add the emission data, we first check the cache for existing entries.
# Save any entries not found into `ghg_request_file` which is then sent to atmosfair data provider.
# Responses are then automatically added to cache.
####


# vvvv Add GHG Emissions
# Note that here, legs_with_ghg does not take into account pax_count > 1, so this not correct data yet.
[legs_with_ghg, ghg_request_file] = merge_emissions(all_legs_nohr)

if ghg_request_file:
    user_todos.append(
        f"\nPlease send file {ghg_request_file} to atmosfair to complete missing GHG data.")
else:
    print('Info: atmosfair status: Complete match, no atmosfair data request needed.')
    # Optional: cross-check that we have atmosfair data for all legs.
    print('TODO: Decide whether running comprehensive atmosfair test')
    # atmosfair_test(all_legs_nohr, ghg_request_file, legs_with_ghg)
# ^^^^ Add GHG Emissions

####
# Find out locations etc. by airport iata codes.
####

# vvvv AIRPORTS
[airport_info, missing_ports] = get_legs_airport_data(all_legs_nohr)

# Note: in the atmosfair ghg response we might see that some of the "airports" we provided are
# in reality train stations (some air tickets can refer to trains).
#
# So only if we have no ghg_request_file left to query, we will positively know that remaining
# missing ports are actual missing data, as opposed to train stations we'll not need anymore
# after atmosfair sent that clarification.
# However, there's no code around that - logic would need to avoid coming across as confusing
# to the user.
print('TODO: Remove airports and legs which atmosfair classifies as train stations.')
if len(missing_ports):
    user_todos.append(
        f"Please extend the airports extension file with the missing entries: {', '.join(missing_ports)}")

airport_info.to_json(f"{output_folder}/airports.json", orient="index")
# ^^^^ AIRPORTS

# vvvv Add demographics.
# hr_issue_list: year, pax_name, employee_id8, comment, found in excerpts
[demographics, hr_issue_list_add2] = demographics_by_year(all_legs_nohr)
legs_full = merge_demographics(legs_with_ghg, demographics)

# A dict of org and their fte count.
dep_fte = get_org_fte()


if len(hr_issue_list_add2):
    hr_issue_list = pd.concat(
        [hr_issue_list, hr_issue_list_add2], axis=0)

if len(hr_issue_list):
    path = f'{output_folder}/hr_issue_list.xlsx'
    to_excel(hr_issue_list, path, index=False)
    user_todos.append(f"Please fix the HR issues listed in {path}")

# ^^^^ Add demographics

# Some rows in the flight legs have a "pax count > 1". This happens when a single
# employee reports the same flight trip for a group of colleagues.
# To get a processable dataset, we need to expand those rows.
# This creates `pax_count` rows out of one, repeating the emissions.
# Some data like the employee id8 is deleted on duplicates, as we don't know the
# employee ids of additional travelers.
legs_full = expand_pax_counts(legs_full)

# This will be the identifiable list for the interal archive.
# NOTE for now it is with pax count normalized to == 1. If not, need to multiple ghg stuff with pax count.
to_excel(legs_full,
         f'{output_folder}/legs_archive_{file_timestamp()}.xlsx', index=False)

legs_full.rename(columns={atmos_def['distance']: 'km'}, inplace=True)

# Limit the dataframe to the data we actually use.
# TODO: The list here appears non-DRY. Would it make sense to keep item definitions in the
# respetive import files, or other solution?
legs_full = legs_full[
    ['trip_id', 'from', 'to', 'class', 'leg_date', 'flight_number', 'leg_date_unknown',
     'flight_reason', 'aircraft_type', atmos_def['co2rfi2'], atmos_def['co2'], 'km']
]

print('TODO: k-anonymization on person-specific data per separate report.')

legs_full_anon = move_dates(legs_full)

print('TODO: Are we still excluding 2021 flights?')
legs_full_anon = exclude_newer(legs_full_anon, '2020-12-31')
anon_dict = legs_full_anon.to_dict(orient='records')

# Remove unnecessary bytes. This might be less relevant once we normalize.
# Also, we could use different data structures to save space (arrays instead of dicts).
# However, we need to have first a nicely readable representation, and only in a second step,
# a more compact format. Because the requirement for static inlining of the resource might
# fall away in future when there might be a more dynamic database.
# TODO: Add dep_fte to the json
compacted = compact_dict(anon_dict)

write_json(f"{output_folder}/anon-legs.json", compacted)

# Print list of things for the user to fix.
if len(user_todos):
    print('\n\nThe following data issues were found:')
    print('- ' + '\n- '.join(user_todos))
    print('\nPlease correct the issues and re-run this program.')
else:
    print('Everything completed successfully.')
