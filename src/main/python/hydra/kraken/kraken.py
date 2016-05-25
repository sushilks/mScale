__author__ = 'AbdullahS'

import sys
from pprint import pprint, pformat  # NOQA
from optparse import OptionParser
import logging
from hydra.lib import util
from hydra.lib.h_analyser import HAnalyser
from hydra.lib.runtestbase import RunTestBase

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
        soon...
        """

class RunTest(object):
    def __init__(self, argv):
        usage = ('python %prog --test_duration=<time to run test>')
        parser = OptionParser(description='KRAKEN !!!',
                              version="0.1", usage=usage)
        parser.add_option("--test_duration", dest='test_duration', type='float', default=10)

        (options, args) = parser.parse_args()
        if ((len(args) != 0)):
            parser.print_help()
            sys.exit(1)
        r = Kraken(options, False)
        r.start_appserver()
        res = r.release_the_kraken()
        r.delete_all_launched_apps()
        print("RES = " + pformat(res))
        if not options.keep_running:
            r.stop_appserver()
        else:
            print("Keep running is set: Leaving the app server running")
            print("   you can use the marathon gui/cli to scale the app up.")
            print("   after you are done press enter on this window")
            input('>')
            r.stop_appserver()
