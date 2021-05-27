import pandas as pd
import datetime as dt
from parse_number import parse_number
from cached_csv_from_xls import get_or_cache
from trip_id import create_assign_trip
import math
import re
from excel_writer_formatted import to_excel

from config import config

# Deps as they occur in BTA file.
_deps = {
    'Life Sciences & Facility Managment': 'N',
    'Departement Angewandte Linguistik': 'L',
    'Departement Gesundheit': 'G',
    'School of Management and Law': 'W',
    'Rektorat': 'R',
    'Departement Soziale Arbeit': 'S',
    'School of Engineering': 'T',
    'Departement Angewandte Psychologie': 'P',
    'Finanzen & Services': 'V'
}


def _resolve_bta_department(bta_dep):
    if not bta_dep in _deps:
        raise Exception(
            f'BTA department {bta_dep} occurring first time; add it to the code.')

    return _deps[bta_dep]


# BTA to atmosfair a.k.a canonical map.
bta_fare_class_map = {'F': 'F', 'Y': 'Y', 'C': 'B', 'W': 'P'}

originals_folder = config['General']['originals_folder']


default_cols = {
    'leg_date_unknown': False,
    'comment': '',
    'provenience': 'BTA',
    'cost': 0,
    'flight_reason': '',
    'flight_reason_other': ''
}


def add_default_cols(legs):
    for (key, value) in default_cols.items():
        legs[key] = value


print('TODO: Add Cost from first row always, perhaps Error on cost 0')

# Reading excel works (see requirements.txt) but is super slow.
bta_csv_paths = [get_or_cache(
    f"{originals_folder}/{item}") for item in config['legs']['bta']]

# unused..
_seconds_in_day = 24 * 60 * 60


def _days_difference(date1, date2):
    difference = date1 - date2
    return divmod(difference.days * _seconds_in_day + difference.seconds, 60)


def _get_defined_routing_cols(row):
    # Slice all legs
    legs = row["Routing 1":"Routing 12"]
    # turn them into array, only take those that are defined.
    legs = [col for (j, col) in enumerate(legs) if pd.notna(legs[j])]
    return legs


def _to_float(str):
    return float(re.sub("[\.']", '', str))


def _sorted_rows(df):
    # row['Dossier No'] + \
    def sort(row): return \
        row['Pax'] + \
        str(-math.copysign(1, _to_float(
            row['Airline Km']))) + pd.to_datetime(_extract_routing_columns(row['Routing 1'])['leg_date'], dayfirst=True).strftime('%Y-%m-%d') + \
        row['Ticket N°2']

    sorted = df.iloc[df.apply(sort, axis=1).argsort()]

    return sorted


def _find_positive_match(df, neg_row):
    # Identify what we're looking for.
    km = abs(_to_float(neg_row['Airline Km']))

    def mask(row):
        # since out/inbound leg pairs have same everything, get 2 hits often. We try narrowing down by
        # adding the check for 'From Destination'
        # Also, ticket numbers or similar can be all different between booking and cancellation.
        # row['Ticket N°2'] == neg_row['Ticket N°2'] and \
        # got better than this: same all of routing.
        # _extract_routing_columns(row['Routing 1'])['leg_date'] == _extract_routing_columns(neg_row['Routing 1'])['leg_date'] and \
        # But: We are checking first routing col equality only because we got some trips where only a single leg is cancelled: 3056119942
        # Sometimes: multiple single-leg cancellations for 1 multi-leg trip: 3056119943
        # I can't use Departure Date col for a match: 5910418675
        # Letting this be for a min:
        # _get_defined_routing_cols(neg_row)[0] in _get_defined_routing_cols(row) and \
        # Sometimes I have seen flights canceled from one dep and re-booked in another (3270120403). Can't do anything about this.
        return _to_float(row['Airline Km']) == km and \
            row['Pax'] == neg_row['Pax'] and \
            row['To Destination'] == neg_row['To Destination'] and \
            row['From Destination'] == neg_row['From Destination']
        # _days_difference(_extract_routing_columns(row['Routing 1'])['leg_date'], _extract_routing_columns(neg_row['Routing 1'])['leg_date']) < 11

    match = df[df.apply(mask, axis=1)]

    if match.shape[0] == 0:
        print(
            f"No booked leg found for cancelled leg with Ticket N°2 {neg_row['Ticket N°2']}, Pax {neg_row['Pax']}, From {neg_row['From Destination']}, To {neg_row['To Destination']}")
        return None

    # Sometimes we just can't distinguish trips.. (e.g. Ticket N°2: 1694912232). Then, pick any
    # if match.shape[0] > 1:
    #     raise Exception(f"Multiple booked matches found for cancelled leg {neg_row.to_string()}")

    return match.head(1).index


def _process_cancellations(df):
    for index, row in df.iterrows():
        # If this is negative, it's a cancellation
        km = _to_float(row['Airline Km'])
        if km >= 0:
            continue

        # Found a cancellation.
        positive_row_index = _find_positive_match(df, row)

        df.drop(index, inplace=True)

        if positive_row_index is not None:
            df.drop(positive_row_index, inplace=True)

    return df


def _bta_fare_class_to_canonical(cls=''):
    if cls == '':
        return cls

    return bta_fare_class_map[cls].upper()


# Routing columns definitions to use in _extract_routing_columns
routing_columns = ['from', 'to', 'airline',
                   'nr', 'class orig', 'class', 'leg_date']


def _extract_routing_columns(routing_str):
    entries = [e.strip() for e in routing_str.split('|')]

    dic = dict(zip(routing_columns, entries))

    new_dic = {key: dic[key] for key in ['from', 'to']}
    new_dic['class'] = _bta_fare_class_to_canonical(dic['class'])
    new_dic['leg_date'] = pd.to_datetime(dic['leg_date'], dayfirst=True)
    new_dic['flight_number'] = dic['airline'] + dic['nr']

    # and convert stuff to upper case
    new_dic['class'] = new_dic['class'].upper()
    new_dic['flight_number'] = new_dic['flight_number'].upper()
    new_dic['from'] = new_dic['from'].upper()
    new_dic['to'] = new_dic['to'].upper()

    # if dic['class orig'] and dic['class orig'] not in classes[dic['class']]:
    #     classes[dic['class']].append(dic['class orig'])
    # if not dic['class orig'] and dic['class'] not in classes['unknown']:
    #     classes['unknown'].append(dic['class'])

    # print(classes)
    return new_dic


# Correctly parse dates (used for filtering only 2017+ years afterwards)
all_years = [pd.read_csv(path, dtype=str, parse_dates=[
    'Departure Date'], dayfirst=True) for path in bta_csv_paths]

bta_orig = pd.concat(all_years, axis=0)


#########
# 1. Fix up the travel dataset before processing it.
#########

# Remove empty rows
bta_orig = bta_orig.loc[bta_orig['Departure Date'].notna()]

# Fixing dates is not needed anymore.
# bta_orig["Departure Date"] = pd.to_datetime(bta_orig["Departure Date"], dayfirst=True)
# Limit the records counted
bta_orig = bta_orig[bta_orig['Departure Date'].dt.year >= 2017]

# to_excel(bta_orig, 'output/bta_precancel.xlsx', index=False)
# bta_orig = _process_cancellations(bta_orig)
# to_excel(bta_orig, 'output/bta_postcancel.xlsx', index=False)
# pandas always keeps the old indices in mutated datasets unless they are reset.
# Since we are making index-based calculations in the iterrows() call, we need a reset.
bta_orig.reset_index(inplace=True)

# sort the dataset
# bta_orig = _sorted_rows(bta_orig)

# Create a trip increment function without any dependencies: each call creates a new trip.
assign_trip = create_assign_trip()

#########
# 2. Copy relevant data from resulting original dataset
#########

# Future: collect PID Sales Amount? Note additional "Price" tag.
bta_list = []
next_index = 0
ref_index = 0
check_cols = []

neg_count = 0

for index, row in bta_orig.iterrows():
    is_neg = parse_number(row['Airline Km']) < 0
    if is_neg:
        neg_count += 1

    if (index < next_index):
        dupes = row["Routing 1":"Routing 12"]
        dupes = [col for (j, col) in enumerate(dupes) if pd.notna(dupes[j])]

        if len(dupes) != len(legs) or len([col for (j, col) in enumerate(dupes) if legs[j] != col]):
            print(f'reference record (row {ref_index + 2})')
            print(legs)
            print(f'new record (row {index + 2})')
            print(dupes)
            raise Exception('Records should be same but are not')

        continue

    legs = _get_defined_routing_cols(row)

    dic = {}
    dic['pax_name'] = row['Pax']
    # pax_count is used for
    # i) Creating the one_off cumulative leg list customer sent to atmosfair for their analysis pdf.
    # ii) For the atmosfair_test assert check to count overall legs.
    dic['pax_count'] = '1'
    # NOTE: We'll save this into the bta df but it is only used to show this to the
    # user that manually matches pax names to similar HR records.
    # If there is no match (NN) and people are considered guests,
    # they are NOT assigned a department as our strategy currently is
    # "assign employee departments", not "assign sponsoring department"
    dic['booking department'] = _resolve_bta_department(row['Department'])
    dic['trip_id'] = assign_trip()
    # dic['km'] = parse_number(row['Airline Km']) / len(legs)

    route_list = [_extract_routing_columns(row) for row in legs]

    records = [{**dic, **route_info} for route_info in route_list]

    if not is_neg:
        bta_list.extend(records)
    ref_index = index
    next_index = index + len(legs)

if neg_count:
    print(
        f'dataset has {neg_count} cancellations left as trips. Check those manually.')

# pd.from_records?
bta_final = pd.DataFrame(bta_list)

add_default_cols(bta_final)


def bta_legs_import():
    return bta_final
