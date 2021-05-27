from datetime import datetime
import math

def file_timestamp():
    return datetime.now().strftime('%Y%m%d%H%M')


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier
