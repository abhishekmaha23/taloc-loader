###
# Situation/Data:
# ===============
# We have HR excerpts from end of each year. Sometimes we have records in-between.
# A very substantial number of people changes FTE, employee type, department, so we need a way to track these.
# We note that most of the time, when people change jobs, there is no indication of when exactly this happened.
# We only have the excerpts to triangulate this. (Dec 31, 2017: n% FTE; Dec 31, 2018: m% FTE)
# Also, Eintritt/Austritt can get updated e.g. if a limited-time contract becomes a regular contract,
# but they also don't give an indication of department and other changes.
#
# Solution:
# =========
# We arbitrarily define that HR details of 20xx1231 are valid for all of 20xx.
# We raise an exception if a person does not exist in the year of their flight, and will see if we get through with this.
# (Alternatively, we could check arbitrary "surrounding" years. This impacts the FTE count but we don't mind, see FTE point below).
#
# Because the FTE count is a snapshot at the end of the year anyway, we don't look at Eintritt/Austritt dates to
# adjust it (e.g. if someone has an Eintritt during that year, say in H2, then we don't halve the FTE count).
#
# Finally, one consequence is that if missing HR records are later found, we need to add them to each year's year-end excerpt
# that this person's Eintritt/Austritt dates (even partially) touch.
# The reason is to a) find the person in that year and b) adjust the FTE tally for the year.
# This will also take care of duplicate people records within the same "missing data" file.
# Note: Consequently, every year of additional records needs to conform to the HR data column definitions of that given year!
# Attention that this definition changes at some point in time.
###

import pandas as pd
import numpy as np
from cached_csv_from_xls import get_or_cache
from config import config
from util import round_half_up
from string import ascii_uppercase

originals_folder = config['General']['originals_folder']

# Got a single person outside allowed departments, not good.
_allowed_departments = list(
    map(lambda x: x.casefold(), config['HR']['top_departments']))


def _round(num):
    return round_half_up(num, 2)


# We consume issues in the app for further processing
hr_issues = []


# NOTE: Column names don't match up: (e.g. Jahr vs Jhr)
#
# 2017
# Personalnummer bis 2018,Anstellungs-Nr,PersNr,Kurzzeich.,Nachname,Vorname,Geb. Jahr,Anrede,Kaderstufe,Kostenst.,Kostenstelle,OEKürzel,Organisationseinheit,Mitarbeiterkreis,Vertrags-BG,Lohn-BG,Eintritt,Austritt
# 2018
# Personalnummer bia 2018,Anstellungs-Nr,PersNr,Kurzzeich.,Nachname,Vorname,Geb. Jhr,Anredeschlüssel,Kaderstufe,Kostenst.,Kostenstelle,OEKürzel,Organisationseinheit,Mitarbeiterkreis,Vertrags-BG,Lohn-BG,Eintritt,Austritt
# 2019
# PersNr,Kurzzeich.,Nachname,Vorname,Geb. Jahr,Anredeschlüssel,Kaderstufe,Kostenst.,Kostenstelle,OEKürzel,Organisationseinheit,Mitarbeiterkreis,Vertrags-BG,Lohn-BG,Eintritt,Austritt
# 2020
# PersNr,Kurzzeich.,Nachname,Vorname,Geb. Jahr,Anredeschlüssel,Kaderstufe,Kostenst.,Kostenstelle,OEKürzel,Organisationseinheit,Mitarbeiterkreis,Vertrags-BG,Lohn-BG,Eintritt,Austritt
hr_data_paths = config['HR']['excerpts']


# We redefine column names for 2017-2018 because they don't match up (but their structure is the same.).
# E.g.: Geb. Jhr vs Geb. Jahr
# We also redefine them that they match with later years.
# E.g.: Anrede vs Anredeschlüssel.
# NOTES:
# - org label: not unique (some are called "Stab" or "Stab xxx")?
# - level (FS IIIa etc): many don't have it. Better to take employee type
# - BG: It turns out (see document attached p. 5) that the "zugesicherter BG" is actually a
# SAP nomenclature for the "Vertrags-Beschäftigungsgrad", also known as
# "Verfügungs-Beschäftigungsgrad", which forms the basis  for the
# "Vollzeitäquivalente (VZÄ)" because the "Verfügung ist rechtlich und
# strategisch relevant". (>> FTE contract)
cols_starting_2019 = ['employee_id8', 'acronym', 'last name', 'first name', 'yob', 'gender', 'level', 'cost center nr',
                      'cost center label', 'org code', 'org label', 'employee type', 'FTE contract', 'FTE salary', 'work start date', 'work end date']
cols_till_2018 = ['employee_id6', 'employment index'] + cols_starting_2019

# date_cols_orignames = ['Eintritt', 'Austritt']
# NOTE: pandas fails to parse years 9999 (Austritt..) so we change our method.

available_years = list(hr_data_paths)
available_years.sort()


def to_iso_str(day_first_date):
    date_comps = day_first_date.split(' ')
    if not len(date_comps) == 2 or not date_comps[1] == '00:00:00':
        raise Exception(f'Error: parsing issue at date {day_first_date}')

    return date_comps[0]


def _read_single_year(year):
    csv_paths = [get_or_cache(f"{originals_folder}/{filename}")
                 for filename in hr_data_paths[year]]

    dfs = []
    for path in csv_paths:
        # na_filter avoids department named "NULL" becoming NaN
        df = pd.read_csv(
            path, dtype=str, na_filter=False)
        # set columns inside loop, otherwise we'll aggregate different columns when HR excerpts have slight column
        # naming mismatches.
        df.columns = cols_till_2018 if year < 2019 else cols_starting_2019
        dfs.append(df)

    df = pd.concat(dfs)
    df['year'] = year

    # NOTE: We don't currently want to parse these as dates because that makes
    # the excel export more tedious.
    # NOTE 2: The end date (aka 'Austritt') has a 9999 year which
    # fails to parse as a datetime in pandas (out of bounds).
    df['work start date'] = df.loc[:, 'work start date'].apply(to_iso_str)
    df['work end date'] = df.loc[:, 'work end date'].apply(to_iso_str)

    # As we are doing calculations with FTEs, convert to float.
    # Also, normalize to ratio instead of percentage
    df['FTE contract'] = df.loc[:, 'FTE contract'].astype('float') / 100
    df['FTE salary'] = df.loc[:, 'FTE salary'].astype('float') / 100

    return df


excerpts_by_year = pd.concat([_read_single_year(year)
                              for year in available_years])
excerpts_by_year['full name'] = (
    excerpts_by_year['last name'] + ' ' + excerpts_by_year['first name'])

# NaN as '' to better calculate.
excerpts_by_year['org code'].fillna('', inplace=True)

invalid_departments = excerpts_by_year[~excerpts_by_year['org code'].str.casefold(
).str.get(0).isin(_allowed_departments)]

# Adjust shape for logging
hr_issues = pd.DataFrame.copy(invalid_departments)

if len(hr_issues):
    hr_issues.loc[hr_issues['org code'] == '',
                'comment'] = 'HR excerpt missing org code'
    hr_issues.loc[hr_issues['org code'] != '', 'comment'] = hr_issues.apply(
        lambda row: f'HR excerpt invalid org code {row["org code"]}', axis=1)

    hr_issues = hr_issues.loc[:, ['year', 'employee_id8', 'comment', 'full name']]
    hr_issues.rename(columns={'full name': 'HR name'}, inplace=True)

# Customer request for 'top level department' which has the first org code letter.
excerpts_by_year['top level department'] = excerpts_by_year['org code'].str.get(0)

# Check the HR excertps for some common errors.
employee_dict = {}
duplicate_employees = {}
for _, row in excerpts_by_year.iterrows():
    year = row['year']
    pers_id8 = row['employee_id8']

    if pd.isnull(pers_id8) or pers_id8 == '':
        # We don't expect this to happen; all excerpts have it.
        raise Exception(
            f'Abort: missing 8-digit Personalnummer in HR excerpt of year {year}:\n{row}.')

    if pers_id8 not in employee_dict:
        employee_dict[pers_id8] = {}

    if year in employee_dict[pers_id8]:
        if year not in duplicate_employees:
            duplicate_employees[year] = []
        duplicate_employees[year].append(pers_id8)

    employee_dict[pers_id8][year] = {key: row[key]
                                     for key in cols_starting_2019}

if len(duplicate_employees.keys()):
    for year in duplicate_employees:
        print(
            f"Duplicate employee numbers {', '.join(duplicate_employees[year])} in HR excerpt of year {year}")
    raise Exception('Aborting because of duplicate employee keys issue')


employees = pd.DataFrame.copy(
    excerpts_by_year[['employee_id8', 'employee_id6', 'full name']])  # , 'year']])

# NOTE: Here we need to be careful as HR records across different years can list
# multiple names for the same employee id.
# This could be due to actual name changes or variation in writing the same name.
# Specifically, we should not try to create a map where the keys are ids and the
# values are names.
employees = employees.groupby(['full name'], sort=True, as_index=False).first()

# Dict of { employee name: employee id8 }
id8_by_fullname = dict(zip(employees['full name'], employees['employee_id8']))

employee_id8_years = pd.DataFrame.copy(
    excerpts_by_year[['employee_id8', 'year']]
)
employee_id8_years['years'] = employee_id8_years['year'].apply(str)
employee_id8_years = employee_id8_years.groupby(
    ['employee_id8'], sort=True, as_index=False
).agg({'years': ', '.join})


# Department names are nested, i.e. department XYZ is under XY.
# If we have a sub-department XYZ, but no super-department XY, this is an issue and needs correction.
# For example: With no org 'LD', but orgs 'LDA' and 'LDB' the cockpit cannot present a correct
# sunburst ring for 'level 2 departments'.
def _complete_missing_deps(sum_fte):
    missing = []
    for year in available_years:
        curr_year = sum_fte[year]

        # Find all org codes to check ancestors for.
        for org_code in list(filter(lambda x: len(x) > 1, curr_year.keys())):
            # We need to approach this from top department (short) to sub-department (long)
            # Otherwise, we'll add sub-sub-departments with FTE, then sub-deps with factor 2 FTE.
            for ancestor in [org_code[:-len(org_code)+i] for i in range(1, len(org_code))]:
                if ancestor not in curr_year:
                    if ancestor not in missing:
                        missing.append(ancestor)

                    all_suborgs = list(
                        filter(lambda code: code.startswith(ancestor), curr_year.keys()))
                    fte = _round(sum([curr_year[suborg]['fte']
                                      for suborg in all_suborgs]))
                    count = int(_round(sum([curr_year[suborg]['count']
                                        for suborg in all_suborgs])))
                    curr_year[ancestor] = {'fte': fte, 'count': count}

    if len(missing):
        print(f'Info: The following org codes had no direct HR entry and were added by this program: ' + ', '.join(missing))


# This is important as otherwise per FTE count gets to be infinite which is not useful for charts.
# Deal with this when we get to it.
def _verify_no_zero_deps(sum_fte):
    zeroes = {}
    for year in available_years:
        curr_year = sum_fte[year]

        for org_code in curr_year.keys():
            # Could use 'count' too
            if curr_year[org_code]['fte'] == 0:
                if year not in zeroes:
                    zeroes[year] = []

                zeroes[year].append(org_code)

    if len(zeroes.keys()):
        z_list = '; '.join(
            [': '.join([str(year), ', '.join(zeroes[year])]) for year in zeroes.keys()])
        raise Exception(
            f'The following departments have a 0 FTE count, which is a problem for calculating per FTE counts: {z_list}')


def get_org_fte():
    # Finally, a per-year list of org codes and total FTEs
    # NOTE: This results in a list where the FTE count of dep 'A' does not include the FTE count of 'AA' etc.
    org_codes_fte = excerpts_by_year.loc[:, ['year', 'org code', 'FTE contract']].groupby(
        # ['year', 'org code'], sort=True, as_index=False).sum('FTE contract')
        ['year', 'org code'], sort=True, as_index=False).agg({'FTE contract': ['sum', 'count']})
    org_codes_fte.reset_index(inplace=True)
    org_codes_fte.columns = [' '.join(col).strip()
                             for col in org_codes_fte.columns.values]

    # Populate sum_fte with the aggregated FTE counts (A has AA too, etc.).
    sum_fte = {}
    for year in available_years:
        year_org_codes = org_codes_fte[org_codes_fte['year'] == year]

        sum_fte[year] = {}

        for _, row in year_org_codes.iterrows():
            org = row['org code']

            with_subdeps = year_org_codes[year_org_codes['org code'].str.startswith(
                org)]
            fte_all = with_subdeps['FTE contract sum'].sum()
            count_all = with_subdeps['FTE contract count'].sum()

            sum_fte[year][org] = {
                'fte': _round(fte_all),
                'count': int(_round(count_all))
            }

    _complete_missing_deps(sum_fte)

    _verify_no_zero_deps(sum_fte)

    _print_deps(sum_fte)

    return sum_fte

# Could print sum_fte here.


def _print_deps(dep_fte):
    deps = []
    for l in ascii_uppercase:
        if l in dep_fte[available_years[0]] or l in dep_fte[available_years[-1]]:
            deps.append(
                [l, [dep_fte[y][l]['fte'] if l in dep_fte[y] else '-' for y in available_years]])

    print(
        f'Info: FTE by departments and years starting {available_years[0]}:', end=' ')
    print(
        ', '.join([f'{d}:{"/".join([str(fte) for fte in ftes])}' for d, ftes in deps]))
