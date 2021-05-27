from datetime import datetime

####
# Filter out all legs of trips if any leg of the trip is newer than iso_date
####
def exclude_newer(legs, iso_date):
    # ref_date = datetime.datetime.strptime(date, '%Y-%m-%d')

    # Add min, max to date per trip
    with_dates = legs.join(legs.groupby('trip_id')[
                           'leg_date'].agg(['min', 'max']), on='trip_id')

    filtered = with_dates[with_dates['max'] <= iso_date]
    # filtered = with_dates[(with_dates['min'] > '2013-01-01') & (with_dates['date'] < '2013-02-01')]
    # trips over year-end:
    # with_dates[(with_dates['min'] <= '2020-12-31') & (with_dates['max'] > '2020-12-31')]
    # filtered = with_dates[with_dates['max'].dt.year <= 2020]

    return filtered.drop(columns=['min', 'max'])
