__author__ = 'sushil'

import logging


def createLogger(name, level=None):
    l = logging.getLogger(name)
    logHandler = logging.StreamHandler()
    logFormatter = logging.Formatter("%(levelname)s %(asctime)s %(filename)s:%(funcName)s:%(lineno)d %(message)s")
    logHandler.setFormatter(logFormatter)
    l.addHandler(logHandler)
    if (level):
        l.setLevel(level)
    return l
