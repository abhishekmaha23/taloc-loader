###
# Idea: A pax_count > 1 means that an employee has paid for someone else's flight.
# We don't know who that other person is but know it's not the same person.
# To avoid assigning the GHG of multiple people to a single trip or person, we add pax_count - 1 flights
# for every row where pax_count > 1.
# In the spirit of cost transparency, we are going to assume that it is a person from the same department
# as the paying person, but we remove personal information otherwise.
# Also, we need to change the trip_id and then remove pax_count.
###
import pandas as pd
import numpy as np

# These are the columns we reset to undefined on paid-for flights.
# Note that we keep flight reason.
unknown_cols_if_paid = ['pax_name', 'employee_id8', 'employee_id6', 'employment index', 'acronym', 'last name',
                        'first name', 'yob', 'gender', 'level', 'FTE contract', 'FTE salary', 'work start date', 'work end date', 'full name']


def expand_pax_counts(orig_legs):
    legs = pd.DataFrame.copy(orig_legs)
    # Prep: integer pax_count
    legs['pax_count'] = legs['pax_count'].astype('int')

    # That's wrong for some, we'll reset it for them later.
    legs['employment subtype'] = legs.apply(
        lambda row: f"paid by {row['employee_id8']}", axis=1)

    # Expand rows where pax_count > 1
    # Helper column to list all pax in a trip of pax_count > 1
    legs['pax id'] = legs['pax_count'].map(lambda x: list(range(1, x+1)))
    legs = legs.explode('pax id')
    legs['trip_id unique'] = legs['trip_id'].astype(
        str) + "_" + legs['pax id'].astype(str)

    # Remove information that is not known about the paid-for co-travelers
    legs.loc[legs.index.duplicated(), unknown_cols_if_paid] = np.nan
    legs.loc[~legs.index.duplicated(), 'employment subtype'] = np.nan
    # Alternative (one col, and set on both conditions):
    # legs['Name'] = np.where(~legs.index.duplicated(keep='first'), legs['Name'], np.nan)
    # legs['employment subtype'] = np.where(legs['Name'].isnull(), legs['employment subtype'], np.nan)

    # Encode Trip ID with unique numerical ID
    legs['trip_id unique'] = pd.Categorical(legs['trip_id unique'])
    legs['trip_id unique'] = legs['trip_id unique'].cat.codes + 1

    # Establish new sort order
    legs.sort_values(by=['trip_id unique', 'leg_date'], inplace=True)

    # Clean up
    legs = legs.reset_index(drop=True)
    legs.drop(columns=['pax_count', 'pax id', 'trip_id'], inplace=True)
    legs.rename(columns={'trip_id unique': 'trip_id'}, inplace=True)

    return legs
