"""
Double-Metaphone implementation in Python.
It was an evolved version of the celebrated Soundex algorithm for phonetic matching
in English.
Devloped by Lawrence Philips in 1990, its variants such as Metaphone 3 is still
widely used today.
"""

from metaphone import doublemetaphone
from enum import Enum

class Threshold(Enum):
    WEAK = 0
    NORMAL = 1
    STRONG = 2

def double_metaphone(value):
    print(doublemetaphone(value))
    return doublemetaphone(value)

#(Primary Key = Primary Key) = Strongest Match
#(Secondary Key = Primary Key) = Normal Match
#(Primary Key = Secondary Key) = Normal Match
#(Alternate Key = Alternate Key) = Minimal Match
def double_metaphone_compare(tuple1,tuple2,threshold):
    if threshold == Threshold.WEAK:
        if tuple1[1] == tuple2[1]:
            return True
    elif threshold == Threshold.NORMAL:
        if tuple1[0] == tuple2[1] or tuple1[1] == tuple2[0]:
            return True
    else:
        if tuple1[0] == tuple2[0]:
            return True
    return False


"""
Name parsing
"""
import probablepeople
from nameparser import HumanName

def parse_name(string):
    # First try the pretrained CRF model
    try:
        results, class_type = probablepeople.tag(string)
        if class_type != 'Person':
            raise ValueErrort("Skipping ...")
            return None
        # Form full name
        given_name = ""
        if 'GivenName' in results:
            given_name = results['GivenName']
        elif 'FirstInitial' in results:
            given_name = results['FirstInitial']
        surname = ""
        if 'Surname' in results:
            surname = results['Surname']
        elif 'LastInitial' in results:
            surname = results['Surname']
        middle_name = ""
        if 'MiddelName' in results:
            middle_name = results['MiddleName']
        elif 'MiddleInitial' in results:
            middle_name = results['MiddleInitial']
        full_name = (given_name, middle_name, surname)
    except Exception as e:
        # If there are errors, try some rule-based models:
        print('CRF models cannot process this name {}' + e.original_string)
        results = HumanName(string)
        given_name, middle_name, surname = results.first, results.middle, results.last
        full_name = (given_name, middle_name, surname)
    return full_name


def format_name(name):
    """
    We only use the format '(GIVEN) (MIDDLE) (SURNAME),
    but bibtex records may contain some names in the form '(SURNAME), (GIVEN)'.
    Therefore, we may need to convert such a name into our preferred format.
    First, detect if there is a comma in the name string.
    Then convert it into our format.
    """
    if ',' in name:
        name_parts = name.split(',')
        return '{} {}'.format(' '.join(name_parts[:-1]), name_parts[-1])
    return name
