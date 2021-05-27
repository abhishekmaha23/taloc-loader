#####
# Merge the yearly HR records with bta pax names by name.
#
# We start with a list of BTA pax names and a reference HR name list.
# We match the two, proposing a HR name for each BTA pax name by highest similarity.
# We then let the users confirm or deny the proposed match.
#   Possible answers: Y (is match), NR (no match but expect a match), NN (no match and none expected/guest)
#   Files thus filled will serve as input to future runs.
# With this, we have the following situation for a general run:
# 1. Calculate a similarity list
# 2. Merge existing files for manually marked similarities
# 3. We end up with BTA Pax names in following classifications:
#   I) Trivial similarities matches are considered matches without user interaction
#  II) Similarities of the same name pair, marked Y are considered matches
# III) Similarities of unmarked name pairs are pushed out to a new marking request file
#  IV) Similarities of the same name pair, marked NR are raising an Exception.
#   V) Similarities of the same name pair, marked NN are considered guests and ignored
#
# 4. NOTE: We always compare the classifications pair-wise to account for new information.
# For example, after adding HR records, a BTA Pax name previously matched with "A" and marked NN could still end up
# being matched with new HR record "B", which happens to be correct. So the software must facilitate reviewing
# new matches and marking them differently from the old ones.
#####
import pandas as pd
from cached_csv_from_xls import get_or_cache
from excel_writer_formatted import to_excel
from util import file_timestamp, round_half_up
import os
import glob
from config import config

from .name_similarity import name_similarity
from .parse_hr import employees, id8_by_fullname

originals_folder = config['General']['originals_folder']
output_folder = config['General']['output_folder']

proposed_matches_filename = f"{config['HR']['outputs']['proposed_matches_basename']}_{file_timestamp()}.xlsx"
matches_path = f"{originals_folder}/{config['HR']['matches_folder']}"

# Define some column names as they appear on the manual review xls
ask_match_col = 'Correct? (Y/NR/NN)'
bta_pax_col = 'BTA Pax Name'
reference_col = 'Proposed HR Match'
min_date_col = 'flight date min'
max_date_col = 'flight date max'
similarity_col = 'similarity'
# from bta import
book_dep_col = 'booking department'

####
# Convert the columns to user-readable ones.
# If called for trivial matches, force the `matches` flag to 'y'
####

hr_bta_fill_instructions = '''
Filling instructions:
* Enter Y for confirming proposed matches
* Enter NR for rejecting proposed matches but indicating that this BTA Pax will be added to the HR records
* Enter NN for rejecting proposed matches and indicating that this BTA Pax is not expected to match with HR records (guest)
'''


def _bta_id8_map(df):
    result = pd.DataFrame.copy(df)
    result['employee_id8'] = result[reference_col].map(id8_by_fullname)
    result.rename(columns={bta_pax_col: 'pax_name'}, inplace=True)
    return result[['pax_name', 'employee_id8']]


def _format_for_review(similarities, force_match=False):
    result = pd.DataFrame.copy(similarities)
    # Note: renaming leg_date to flight_date so it's clear to users this is across all flights, not a
    # specific one.
    result = result.rename(
        columns={'pax_name': bta_pax_col, 'reference': reference_col, 'leg_date min': min_date_col,
                 'leg_date max': max_date_col})
    # Sort column order:
    result = result[[bta_pax_col, reference_col,
                     similarity_col, min_date_col, max_date_col, book_dep_col]]

    # Make dates user readable
    result[min_date_col] = result[min_date_col].apply(
        lambda x: x.strftime('%Y-%m'))
    result[max_date_col] = result[max_date_col].apply(
        lambda x: x.strftime('%Y-%m'))

    result[ask_match_col] = 'y' if force_match else ''

    return result


####
# Input: bta_legs with names, and through employees, list of names in hr.
# Returns: Array with [similar names, trivially matched names]
####
def _propose_hr_matches(bta_legs_raw):
    # Collect min and max flight dates per pax.
    bta_pax_with_dates = bta_legs_raw.groupby('pax_name', sort=True, as_index=False).agg({
        'leg_date': ['min', 'max'],
        # Get all distinct departments people have been booked on.
        book_dep_col: lambda x: ', '.join(set(x))
    })

    # Flatten "leg_date: min/max" columns into separate "leg_date min", "leg_date max" columns
    # (Avoid flattening for the book_Department col)
    bta_pax_with_dates.columns = [' '.join(col).strip() if not 'lambda' in col[1] else col[0]
                                  for col in bta_pax_with_dates.columns.values]

    # List of all employees per HR records.
    hr_list = employees['full name']

    [proposed_matches, trivial_matches] = name_similarity(
        hr_list, bta_pax_with_dates, 'pax_name')

    proposed_matches = _format_for_review(proposed_matches)
    trivial_matches = _format_for_review(trivial_matches, True)

    return [proposed_matches, trivial_matches]


def _write_review_file(df):
    filepath = f'{output_folder}/{proposed_matches_filename}'
    to_excel(df, filepath, index=False)

    return filepath


def find_hr_matches(bta_legs_raw):
    # First, calculate similarities. We will use the "obvious" similarities right away
    # "matched" are the trivial matches we'll use right away
    # In "similar" will be a lot of proposals, also unlikely ones, for manual review by user.
    [similar, matched] = _propose_hr_matches(bta_legs_raw)

    # All matches are trivial without need for a manual match? Then return matched
    if len(similar) == 0:
        # Note, this is missing a 'matched': 'y' column for all.
        return [_bta_id8_map(matched), None, None]

    # Some non-trivial similarities are left over.
    # Can we resolve all using the match file(s) previously provided by users?
    all_matchfiles_xlsx = glob.glob(os.path.join(matches_path, "*.xlsx"))
    all_matchfiles = [get_or_cache(xlsx) for xlsx in all_matchfiles_xlsx]

    # Trivial case: We have no match files yet to consider.
    if (len(all_matchfiles)) == 0:
        proposed_hr_filepath = _write_review_file(similar)
        return [_bta_id8_map(matched), None, {'output': proposed_hr_filepath, 'input': matches_path}]

    # In this case we have some files to match. Check if they cover all cases.
    manual_matches = pd.concat((pd.read_csv(f, dtype=str)
                                for f in all_matchfiles))

    # Check empty or non-conforming rows in manual input column.
    if manual_matches[manual_matches[ask_match_col].isna()].shape[0] and manual_matches[~manual_matches[ask_match_col].str.casefold().isin(['y', 'nn', 'nr'])].shape[0] > 0:
        raise Exception(
            f"Please verify that all rows in all files inside {matches_path} contain a filled 'y'/'nn'/'nr' choice.")

    # Note: It's possible that records in old match files are later superseded after user adds missing HR data.
    # For example there could be a better match given new names.
    # This is not a problem here because the left join only completes entries that are missing despite new HR data
    # Also, See note point 4 in description about matching on 2 name keys.

    # This keeps additional columns that a user might have added to the previous file,
    # while also making sure marked_similar has the annotations like similarity and min_date_col etc

    # Also: errors ignore because we have preexisting manually filled files where book_dep_col does not yet exist.
    manual_matches_red = manual_matches.drop(
        columns=[min_date_col, max_date_col, book_dep_col, similarity_col])
    similar_red = similar.drop(columns=ask_match_col)
    marked_similar = pd.merge(similar_red, manual_matches_red, how='left', on=[
                              bta_pax_col, reference_col])

    #   I) Trivial similarities matches are considered matches without user interaction
    #      --> already handled in "matched" df
    #  II) Similarities of the same name pair, marked Y are considered matches
    confirmed_similar = marked_similar[marked_similar[
        ask_match_col].isin(['y', 'Y'])]
    # III) Similarities of unmarked name pairs are pushed out to a new marking request file
    unmarked_new = marked_similar[marked_similar[ask_match_col].isna()]
    #  IV) Similarities of the same name pair, marked NR are resulting in a todo for the user.
    marked_nr = marked_similar[marked_similar[ask_match_col].str.casefold(
    ) == 'nr']
    #   V) Similarities of the same name pair, marked NN are considered guests and ignored
    # marked_nn = marked_similar[marked_similar[ask_match_col].str.casefold() == 'nn']

    # Format for use in app (standard pax_name)
    marked_missing = marked_nr[bta_pax_col].tolist()

    # Combination of automatically and manually (user) matched
    all_matched = pd.concat([matched, confirmed_similar])

    name_matches_request = None

    if len(unmarked_new):
        # In this situation, we have some unconfirmed similarities and create a file for it.
        proposed_hr_filepath = _write_review_file(unmarked_new)
        name_matches_request = {
            'output': proposed_hr_filepath, 'input': matches_path}

    # If name_matches_request is None, then all entries in marked_similar are manually matched
    return [_bta_id8_map(all_matched), marked_missing, name_matches_request]


def assign_employee_id8(bta_legs, bta_id8_map, marked_missing):
    result = pd.merge(bta_legs, bta_id8_map, how='left', on='pax_name')

    result['employment'] = result.apply(
        lambda row: 'employee' if pd.notna(row['employee_id8']) or (marked_missing and row['pax_name'] in marked_missing) else 'guest', axis=1)

    # Provide some statistics.
    pax = result.groupby(['pax_name'], sort=True, as_index=False).first()
    pax_total = len(pax)
    annotated = pax[pax['employee_id8'].notna()].shape[0]

    print(
        f'Info: {annotated} of {pax_total} bta pax ({round_half_up(100 * annotated / pax_total, 1)}%) have an employee id, the remaining {pax_total - annotated} are considered guests.'
    )

    return result
