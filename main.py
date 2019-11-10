import json
import logging
import time
from bisect import bisect_left
from urllib3.util.retry import Retry

import envparse
import requests
from envparse import env
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError


envparse.env.read_envfile()

PASS_KEY = env('PASS_KEY')

session = requests.Session()

retries = Retry(total=15,
                backoff_factor=0.1)

session.mount('http://', HTTPAdapter(max_retries=retries))


def get_serial_numbers():
    return list(map(int, open('sl.txt').read().splitlines()))


def get_exception_serial_numbers():
    return list(map(int, open('except.txt').read().splitlines()))


def get_electors():
    return json.loads(open('response.json').read())


def get_progress():
    try:
        return json.loads(open('progress.json', 'r').read())
    except FileNotFoundError:
        pass
    except:
        logging.exception('Error while reading progress')
    return {}


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


def save_progress(progress):
    with open('progress.json', 'w') as fi:
        fi.write(json.dumps(progress))


def verify_elector(elector, progress):
    if str(elector['SLNO_INPART']) in progress:
        return True
    print(f"\n\nVerifying { elector['SLNO_INPART'] }. { elector['EPIC_NO'] }. { elector['FM_NAME_EN'] } ...")

    try:
        data = {
            "STATE_CODE": "S24",
            "AC_NO": "75",
            "PART_NO": "27",
            "SLNO_INPART": str(elector['SLNO_INPART']),
            "EPIC_NO": elector['EPIC_NO']
        }

        response = session.post(
            'http://evpservices.ecinet.in/api/EVP/PostElectorVerificationStatus?st_code=S24&ac_no=75&part_no=27',
            headers={
                'pass_key': PASS_KEY,
                'Content-Type': "application/json",
            },
            data=json.dumps(data)
        )
    except ConnectionError:
        print('\t Failed: ConnectionError')
        return False

    verified = response.status_code == 200 and response.json()['IsSuccess'] is True

    if verified:
        print(f"\tVerified { elector['EPIC_NO'] }")
        progress[str(elector['SLNO_INPART'])] = elector
        save_progress(progress)
    else:
        print(f"\t Failed: { response.status_code } { response.content }")

    return verified


def verify(electors, serial_numbers, progress):
    for number in serial_numbers:
        elector = get_elector(electors, number)
        verify_elector(elector, progress)
    
    print('\n\nCompleted')


if __name__ == '__main__':
    serial_numbers = get_serial_numbers()
    electors = get_electors()
    progress = get_progress()
    verify(electors, serial_numbers, progress)

    all_numbers = {e['SLNO_INPART'] for e in electors}
    verified_numbers = {int(n) for n in progress.keys()}
    unverified_set = all_numbers.difference(verified_numbers)
    
    exception_set = set(get_exception_serial_numbers())

    to_verify_set = unverified_set.difference(exception_set)

    to_verify = list(to_verify_set)
    to_verify.sort()
    print(len(to_verify_set), to_verify)

    verify(electors, to_verify, progress)

    unverified = list(unverified_set)
    unverified.sort()
    for un in unverified:
        elector = get_elector(electors, un)
        print(f"{ elector['SLNO_INPART'] }. { elector['EPIC_NO'] }. { elector['FM_NAME_EN'] }")
    print(len(all_numbers), len(verified_numbers), len(unverified), len(electors))
