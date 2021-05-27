import pandas as pd
from excel_writer_formatted import to_excel
from config import config

output_folder = config['General']['output_folder']

mapping = {}

_name_count = 0


def _create_name():
    global _name_count
    _name_count += 1
    return f'pax{_name_count}'


def get_pseudonym(name):
    # if it's a number
    name = str(name)

    if name not in mapping:
        mapping[name] = _create_name()

    return mapping[name]


def write_mapping():
    origs = list(mapping)
    pseudos = [mapping[name] for name in mapping]

    df = pd.DataFrame({'Original Name/ID': origs, 'Pseudonyms': pseudos})
    to_excel(df, f'{output_folder}/pseudonyms.xlsx', index=False)
