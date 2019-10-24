import json
import logging
from bisect import bisect_left

import envparse
from envparse import env


envparse.env.read_envfile()


PASS_KEY = env('PASS_KEY')


def get_serial_numbers():
    return list(map(int, open('sl.txt').read().splitlines()))


def get_electors():
    return json.loads(open('response.json').read())


def get_progress():
    try:
        return json.loads(open('progress.json', 'r').read())
    except FileNotFoundError:
        pass
    except:
        logging.exception('Error while reading progress')
    return []


def binary_search(t, key, low=0, high=None):
    if not high:
        high = len(t) - 1
    # bisecting the range
    while low < high:
        mid = (low + high)//2
        if t[mid]['SLNO_INPART'] < key:
            low = mid + 1
        else:
            high = mid
    # at this point 'low' should point at the place
    # where the value of 'key' is possibly stored.
    return low if t[low]['SLNO_INPART'] == key else -1


def get_elector(electors, serial_number):
    position = binary_search(electors, serial_number)
    if position >= 0:
        return electors[position]


if __name__ == '__main__':
    serial_numbers = get_serial_numbers()
    electors = get_electors()
    progress = get_progress()
    print(PASS_KEY, serial_numbers, progress, len(electors), len(serial_numbers))
    for number in serial_numbers:
        get_elector(electors, number)
