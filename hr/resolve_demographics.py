####
# Idea:
# - Reduce the leg dataset to [employee_id8, year]
# - Left-merge this with the excerpts.
# - fail if we have n.a. records
#   - optionally, can indicate if there are employees for failed records (in other years)
####

import pandas as pd
from .parse_hr import employee_id8_years, excerpts_by_year

# ['pax_name', 'pax_count', 'trip_id', 'from', 'to', 'class', 'leg_date',
#       'flight_number', 'leg_date_unknown', 'comment', 'provenience', 'cost',
#       'flight_reason', 'flight_reason_other', 'employee_id8', 'employee_id6']


def _years_found(row):
    return ', '.join(employee_id8_years[employee_id8_years['employee_id8']
                                        == row['employee_id8']]['years'])


def demographics_by_year(all_legs_nohr):
    leg_id8years = all_legs_nohr[[
        'leg_date', 'employee_id8', 'pax_name']].copy()
    leg_id8years['year'] = leg_id8years['leg_date'].dt.year
    leg_id8years.drop(columns=['leg_date'], inplace=True)
    # This drops nan employee_id8
    leg_id8years = leg_id8years.groupby(
        ['year', 'employee_id8'], sort=True, as_index=False).first()

    # First: We may only merge leg_id8years combos that actually have an employee_id8.
    # The others are considered guests.
    print('TODO: For guests, or all without HR: estimate gender.')

    # This is a no-op. All of them are defined after the groupby
    # leg_id8years = leg_id8years[leg_id8years['employee_id8'].notna()]

    merged_hr = pd.merge(leg_id8years, excerpts_by_year,
                         how='left', on=['employee_id8', 'year'])

    # merge failures
    missing_hr = merged_hr[merged_hr['work start date'].isna()].copy()

    # prepare for sending this to user: subset of records
    missing_hr = missing_hr[['year', 'pax_name', 'employee_id8']]

    if len(missing_hr):
        missing_hr.sort_values(by=["year", "employee_id8"], inplace=True)
        missing_hr['comment'] = 'Pax has employee id(8) which is not in the HR excerpt of their flight year'

        missing_hr['found in excerpts'] = missing_hr.apply(
            lambda row: _years_found(row), axis=1)

        # print('Some travelers have employee ids but are missing in the HR excerpt of their flight year. Adding these to the hr issue list.')

    # merge hits
    matched_hr = merged_hr[merged_hr['work start date'].notna()].copy()

    # For further processing, remove pax_name (which is originally from legs)
    matched_hr.drop(columns='pax_name', inplace=True)
    return [matched_hr, missing_hr]


def merge_demographics(legs, matched_hr):
    merge_legs = pd.DataFrame.copy(legs)
    # NOTE: legs post GHG have a string leg_date (because of the date matching),
    # while before it's a datetime (because of optimizing parsing).
    # This might be considered an issue.
    merge_legs['leg_date_helper'] = pd.to_datetime(merge_legs['leg_date'])

    # We merge HR excerpts year-wise, so this is important
    merge_legs['year'] = merge_legs['leg_date_helper'].dt.year

    # Since we don't key on this, we'll get multiple copies if we don't drop it.
    merge_hr = matched_hr.drop(columns='employee_id6')

    merged = pd.merge(merge_legs, merge_hr,
                      how='left', on=['employee_id8', 'year'])

    # Now, can drop year because we have leg_date
    merged.drop(columns=['year', 'leg_date_helper'], inplace=True)

    return merged
