__author__ = 'sushil'

import logging
import string

text_characters = "".join(map(chr, range(32, 127))) + "\n\r\t\b"
_null_trans = string.maketrans("", "")


def createlogger(name, level=None):
    l = logging.getLogger(name)
    log_handler = logging.StreamHandler()
    log_formatter = logging.Formatter("%(levelname)s %(asctime)s %(filename)s:%(funcName)s:%(lineno)d %(message)s")
    log_handler.setFormatter(log_formatter)
    l.addHandler(log_handler)
    if (level):
        l.setLevel(level)
    return l


def istext(s, text_characters=text_characters, threshold=0.00):
    if "\0" in s:
        return False
    if not s:
        return True
    # Get the substring of s made up of non-text characters
    t = s.translate(_null_trans, text_characters)
    return (1.0 * len(t)) / (1.0 * len(s)) <= threshold
