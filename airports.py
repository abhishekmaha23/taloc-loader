import pandas as pd
from config import config


def try_unicode(str):
    try:
        return str.encode('latin1').decode('utf-8')
    except Exception:
        return str


originals_folder = config['General']['originals_folder']
airports_ext = config['General']['airports_extended']

# openflights database
# airport_database = pd.read_csv("assets/airports.csv")

# datahub.io
airport_database_orig = pd.read_csv('assets/airport-codes_csv.csv')

airport_extension = pd.read_csv(f'{originals_folder}/{airports_ext}')

airport_database = pd.concat([airport_database_orig, airport_extension])

# datahub-specific: need to remove "closed" records as otherwise we get duplicate
# iata codes (e.g. HKG, MUC)
airport_database = airport_database[airport_database['type'] != 'closed']
# harmonize this with current code for now
airport_database = airport_database.rename(
    columns={'iso_country': 'country', 'municipality': 'city', 'iata_code': 'iata'})
# Convert Ã¼ to ü etc.
# TODO: Find a better source or improve how we get the datahub data.
airport_database['country'] = airport_database.apply(
    lambda row: try_unicode(row['country']), axis=1)
airport_database['city'] = airport_database.apply(
    lambda row: try_unicode(row['city']), axis=1)


# Get a frame of unique iata entries used in iata_series_list, together with
# airport info such as city, etc.
# This is later stored in cockpit.
def _legs_airport_info(*iata_series_list):
    iata_series = pd.concat(iata_series_list, axis=0)
    iata = pd.DataFrame(
        {'iata': iata_series.str.upper().sort_values().unique()})

    airport_info = pd.merge(iata, airport_database, how='left', on='iata')
    airport_info[['lon', 'lat']] = airport_info['coordinates'].str.split(
        ', ', 1, expand=True)
    airport_info.lon = airport_info.lon.astype('float')
    airport_info.lat = airport_info.lat.astype('float')
    airport_info = airport_info[['city', 'country', 'iata', 'lon', 'lat']]

    iata_dupes = list(airport_info[airport_info['iata'].duplicated()]['iata'])
    if len(iata_dupes):
        raise Exception(
            f"Unexpected error: airport_info has duplicate iata codes {', '.join(iata_dupes)}")

    airport_info = airport_info.set_index('iata')

    return airport_info

###
# Which iata codes are missing in the airport_database database?
###


def _missing_iata_definitions(airport_info):
    missing_ports = airport_info[airport_info['city'].isna()]
    missing_ports.reset_index(inplace=True)

    return list(missing_ports['iata'])


def get_legs_airport_data(legs):
    # Create the airport file to be loaded into the cockpit.
    airport_info = _legs_airport_info(legs['from'], legs['to'])

    # Our airport database may not be complete. Check if the airport_info file is missing data for any iata files.
    missing_ports = _missing_iata_definitions(airport_info)

    return [airport_info, missing_ports]
