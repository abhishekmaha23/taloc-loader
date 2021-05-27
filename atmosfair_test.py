import pandas as pd
from df_to_list import df_to_list

from atmosfair import atmos_def

from config import config

originals_folder = config['General']['originals_folder']


def has_atmos_leg(ref_leg):
    return lambda test_leg: test_leg['from'] == ref_leg['from'] and test_leg['to'] == ref_leg['to'] and test_leg['flight_number'] == ref_leg['flight_number'] and test_leg['leg_date'] == ref_leg['leg_date'] and test_leg['class'] == ref_leg['class']


####
# This tests the situation where there is no need for an atmosfair transfer.
####
def atmosfair_test(legs, missing_filename, legs_with_ghg):
    print(f'Testing atmosfair load.')

    assert missing_filename == None
    # We have no leg marked as incomplete.
    print('Checking overall numbers match ...', end=" ")
    assert len(legs_with_ghg[legs_with_ghg[atmos_def['co2']].isna()]) == 0
    assert legs_with_ghg['pax_count'].astype(
        'int').sum() == legs['pax_count'].astype('int').sum()
    assert legs_with_ghg.shape[0] == legs.shape[0]
    print('done.')

    print('Checking if every leg finds a match inside the atmosfair cache ...', end=" ")
    legs_copy = pd.DataFrame.copy(legs)
    legs_copy['leg_date'] = legs_copy['leg_date'].dt.strftime('%Y-%m-%d')
    legs_copy.fillna('', inplace=True)
    legs_list = df_to_list(legs_copy)
    atmosfair_list = df_to_list(legs_with_ghg)

    hit_count = 0

    for leg in legs_list:

        hit = list(filter(has_atmos_leg(leg), atmosfair_list))
        if len(hit) == 0:
            raise Exception(f"Miss for {leg}")
        else:
            hit_count += 1

    # We want an atmosfair data hit for every leg in our original files.
    assert(hit_count == len(legs_list))
    print('done.')
