__author__ = 'AbdullahS'

from pprint import pprint, pformat  # NOQA
import logging
from hydra.lib import util
from hydra.kraken.plumgrid.pg_kraken_tests import PGKrakenTestSanity  # NOQA

l = util.createlogger('kraken_factory', logging.INFO)


class KrakenFactory(object):
    '''
    Class dynamically loads the respective DB Test Class
    '''
    _db_factories = {}

    @staticmethod
    def load_kraken_test_factory(db_type, test_name, h_han):
        '''
        Function to statically load respective DB test e-g plumgrid, cassandra etc
        Called by Kraken from kraken.py release_the_kraken()
        @args:
        db_type:        db_type e-g PG
        test_name:      Test to load e-g Sanity
        h_han:          Hydra handle, passed down to respective test class
        '''
        l.info("KrakenFactory.load_kraken_test_factory loading db_type=%s, test_name=%s", db_type, test_name)
        if db_type not in KrakenFactory._db_factories:
            class_to_load = db_type + "KrakenTest" + test_name + ".Factory()"
            l.info("class to load [%s]", class_to_load)
            KrakenFactory._db_factories[db_type] = eval(class_to_load)
        return KrakenFactory._db_factories[db_type].create(h_han)
