_trip_id = -1

###
# checklist: the variables we watch for changes to increment the _trip_id.
# If checklist is not provided, we create a new id on every call (bta)
###
def create_assign_trip(checklist=[]):
    last_check = {k: None for k in checklist}

    def assign_trip(row = None):
        global _trip_id

        if not len(checklist):
            _trip_id += 1
            return _trip_id

        if row is None:
            raise Exception('function constructed with checklist, needs row param')

        if any([row[item] != last_check[item] for item in checklist]):
            for item in checklist:
                last_check[item] = row[item]

            _trip_id += 1

        return _trip_id

    return assign_trip
