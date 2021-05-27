import json


def clone(data):
    return json.loads(json.dumps(data))


def remove_if_empty(obj, key):
    # Remove the property if it is not defined (saving space.)
    if not obj[key] or obj[key] == '':
        obj.pop(key)


def write_json(filename, data):
    with open(filename, 'w') as data_file:
        json.dump(data, data_file)


def read_json(filename):
    with open(filename, 'r') as data_file:
        data = json.load(data_file)

    return data


def deep_iterate(obj, fn):
    def get_keys(obj):
        if isinstance(obj, list):
            return list(range(0, len(obj)))
        elif isinstance(obj, dict):
            return list(obj.keys())
        else:
            raise Exception('unhandled data type')
    for key in get_keys(obj):
        if isinstance(obj[key], list) or isinstance(obj[key], dict):
            deep_iterate(obj[key], fn)
        else:
            fn(obj, key)

def compact_dict(obj):
    data = clone(obj)

    deep_iterate(data, remove_if_empty)

    return json.dumps(data)