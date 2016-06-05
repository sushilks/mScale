__author__ = 'AbdullahS'

import sys
from pprint import pprint, pformat  # NOQA
from optparse import OptionParser
import logging
from hydra.lib import util
from hydra.lib.runtestbase import RunTestBase
from hydra.kraken.kraken_factory import KrakenFactory

try:
    # Python 2.x
    from ConfigParser import ConfigParser
except ImportError:
    # Python 3.x
    from configparser import ConfigParser

l = util.createlogger('kraken', logging.INFO)
# l.setLevel(logging.DEBUG)


class Kraken(RunTestBase):
    def __init__(self, options, runtest=True, mock=False):
        self.options = options
        self.config = ConfigParser()
        RunTestBase.__init__(self, 'kraken', self.options, self.config, startappserver=runtest, mock=mock)

    def release_the_kraken(self):
        """
        Loads the factory that loads the appropriate
        class
        """
        return KrakenFactory.load_kraken_test_factory(db_type=self.options.db_type,
                                                      test_name=self.options.test_name, h_han=self)


class RunTest(object):
    def __init__(self, argv):
        usage = ('python %prog --test_duration=<time to run test>')
        parser = OptionParser(description='KRAKEN !!!',
                              version="0.1", usage=usage)
        parser.add_option("--db_type", dest='db_type', type='string', default="PG")
        parser.add_option("--test_name", dest='test_name', type='string', default="Sanity")

        (options, args) = parser.parse_args()
        if ((len(args) != 0)):
            parser.print_help()
            sys.exit(1)
        k = Kraken(options, False)
        k.start_appserver()
        res = k.release_the_kraken()
        k.delete_all_launched_apps()
        print("RES = " + pformat(res))
        k.stop_appserver()
