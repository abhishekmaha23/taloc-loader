####### 
# One-off atmosfair:
# This is an exceptional process applied one time only.
# The goal was to NOT normalize the shipment to atmosfair because the response
# was used in an initial report that was created manually, before our software was completed.
#
# Assumptions:
#  
# - It’s ok that atmosfair receives only an opaque person pseudonym (1, 2, 3, ..) together with the flight legs. atmosfair knows no demographics such as department, etc.
# - However, need to ensure same employee id === same pseudonym to the extent possible (this will work within datasets, but not across to bta because bta is not mapped to employee ids yet)
# - Internally, need to maintain which atmosfair identifier is which actual person id or name (via sms).
#  
# Approach:
#  
# > Today:
#  
# - I finish cleaning bta legs (removing canceled legs, but not yet finding people’s employee ids from their “similar” names)
# - I create a bta legs file with cleaned cancellations, replacing people’s names with pseudonyms for atmosfair (1, 2, 3 or similar) in a consistent way.
# - I change the archive+airplus files, replacing employee ids (=personal data) with same kind of pseudonyms
# - I send you a single file with all these legs
# - I additionally send you 2 xls mapping lists: one has mappings between employee ids and atmos pseudonyms (for archive and airplus legs);
#   one has mappings between person names (per bta convention) and pseudonyms. (-> no employee ids because all similarities not ready)
#  
#  
# > After receiving atmosfair response:
# - You get the atmos report
# - I manually fill the extractor atmosfair cache with the returned data and don’t need an additional atmosfair send in this round (<1hr) I can also help to reconcile data if useful.
#   - remove person ID
#   - normalize to pax: 1
#   - how to deal with pax, charter, ..?
# 
####### 

import pandas as pd
import datetime as dt
from bta_legs_import import bta_legs_import
from regular_legs_import import regular_legs_import
from config import config
from excel_writer_formatted import to_excel

from pseudonymize import get_pseudonym, write_mapping

originals_folder = config['General']['originals_folder']
output_folder = config['General']['output_folder']

flight_info = ['from', 'to', 'class', 'leg_date', 'flight_number']

bta = bta_legs_import()
spesen = regular_legs_import(config['legs']['spesen'])
airplus = regular_legs_import(config['legs']['airplus'])

print('Warning: Per-file provenience is outdated for Airplus and Archive legs')
bta = bta[['pax_name'] + flight_info]
bta['pax_name'] = bta.apply(lambda row: get_pseudonym(row['pax_name']), axis=1)
bta['provenience'] = 'BTA'

spesen = spesen[['employee_id8', 'pax_count'] + flight_info]
spesen['employee_id8'] = spesen.apply(
    lambda row: get_pseudonym(row['employee_id8']), axis=1)
spesen.rename(columns={'employee_id8': 'pax_name'}, inplace=True)
spesen['provenience'] = 'Archive'

airplus = airplus[['employee_id8', 'pax_count'] + flight_info]
airplus['employee_id8'] = airplus.apply(
    lambda row: get_pseudonym(row['employee_id8']), axis=1)
airplus.rename(columns={'employee_id8': 'pax_name'}, inplace=True)
airplus['provenience'] = 'CWTravel'

legs = pd.concat([bta, spesen, airplus])
legs['aircraft'] = ''
legs['charter'] = ''
legs['leg_date'] = legs['leg_date'].dt.strftime('%d.%m.%Y')
legs.rename(columns={'pax_name': 'employeeName', 'pax_count': 'pax', 'leg_date': 'flightDate',
                     'from': 'departure', 'to': 'arrival', 'class': 'travelClass', 'flight_number': 'flightNumber'}, inplace=True)

sorted_cols = ['departure',
               'arrival',
               'pax',
               'travelClass',
               'flightNumber',
               'flightDate',
               'aircraft',
               'charter',
               'employeeName',
               'provenience']

legs = legs[sorted_cols]

to_excel(legs, f'{output_folder}/legs.xlsx', index=False)

write_mapping()

print('one_off complete. Quitting')
quit()
