__author__ = 'sushil'

from pprint import pprint, pformat  # NOQA
import logging
import os
import sys
from optparse import OptionParser
from datetime import datetime
from hydra.lib import util
from hydra.zmqtest.runtest import RunTestZMQ
from hydra.lib.boundary import Scanner

l = util.createlogger('runTestSuit', logging.INFO)
# l.setLevel(logging.DEBUG)


class RunSuitFixed(object):
    def __init__(self, options):
        l.info(" Starting Fixed Rate ....")
        print("print Starting Fixed Rate ....")
        pwd = os.getcwd()
        fname = 'zmqsuit.test.log'
        ofile = open(pwd + '/' + fname, 'w')
        ofile.truncate()
        ofile.write('Starting at :' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')
        # def options = lambda: None  # NOQA

        # setattr(options, 'test_duration', 30)
        # setattr(options, 'msg_batch', 50)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'total_sub_apps', 30)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        setattr(options, 'keep_running', False)
        l.info("RUNNING WITH c_sub=" + pformat(options.c_sub) + " c_pub=" + pformat(options.c_pub))

        self.first_test = None
        # Parameters
        # client_set = [5, 10, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        client_set = [80]
        # client_set = [5, 10, 50, 100, 200, 400]

        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = RunTestZMQ(options, None)
                self.first_test = runner
                self.first_test.start_appserver()
            else:
                runner.set_options(options)
                runner.scale_sub_app()
                # runner = RunTestZMQ(options, None)

            scanner = Scanner(runner.run, 500)
            res = scanner.range(range(35000, 100000, 1000))
            l.info("Found for Client Count %d :" % client_count)
            l.info(" :: " + pformat(res))
        runner.delete_all_launched_apps()
        self.first_test.stop_appserver()
        l.info("TestSuite Compleated.")
        sys.exit(0)


def Run(argv):  # NOQA
    usage = ('python %prog --c_pub --c_sub'
             ' --test_duration=<time to run test> --msg_batch=<msg burst batch before sleep>')
    parser = OptionParser(description='zmq scale maxrate test master',
                          version="0.1", usage=usage)
    parser.add_option("--test_duration", dest='test_duration', type='int', default=15)
    parser.add_option("--msg_batch", dest='msg_batch', type='int', default=100)
    parser.add_option("--c_pub", dest='c_pub', action="store_true", default=False)
    parser.add_option("--c_sub", dest='c_sub', action="store_true", default=False)
    (options, args) = parser.parse_args()
    RunSuitFixed(options)
    return True
