import re

replace_tokens = ["'"]


def parse_number(num):
    # Make sure it's a string (it probably already is).
    value = str(num)

    for token in replace_tokens:
        value = re.sub(re.escape(token), '', value)

    try:
        return float(value)
    except ValueError:
        print('Could not convert', value, 'to integer.')
