__author__ = 'annyz'

from pprint import pprint, pformat  # NOQA
import logging
import os
import sys
from datetime import datetime
from hydra.lib import util
from hydra.kafkatest.runtest import RunTestKAFKA
from hydra.lib.boundary import Scanner
from optparse import OptionParser

l = util.createlogger('runSuitMaxRate', logging.INFO)


class RunSuitMaxRate(object):
    def __init__(self, options):
        l.info(" Starting Max Rate ....")
        pwd = os.getcwd()
        fname = 'kafkasuit.test.log'
        ofile = open(pwd + '/' + fname, 'w')
        ofile.truncate()
        ofile.write('Starting at :' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '\n')

        # setattr(options, 'test_duration', 15)
        setattr(options, 'msg_batch', 100)
        setattr(options, 'msg_rate', 10000)
        setattr(options, 'keep_running', False)
        setattr(options, 'acks', 0)
        self.first_test = None

        # Parameters
        client_set = [30, 60, 90, 180, 500, 1000, 2000, 4000, 8000]

        for client_count in client_set:
            setattr(options, 'total_sub_apps', int(client_count / 10))
            if not self.first_test:
                runner = RunTestKAFKA(options, None)
                self.first_test = runner
                self.first_test.start_appserver()
            else:
                # Keep the old runner
                # But rescale the app
                runner.set_options(options)
                runner.scale_sub_app()

            if client_count < 50:
                scanner = Scanner(runner.run, 30000)
            elif client_count < 200:
                scanner = Scanner(runner.run, 10000)
            else:
                scanner = Scanner(runner.run, 500)
            (status, rate, drop) = scanner.find_max_rate()
            l.info("Found for Client Count %d Max message Rate %d with drop %f" %
                   (client_count, rate, drop))
            maxrate_drop = drop
            maxrate_rate = rate
            if True and maxrate_drop != 0:
                l.info("Searching for no-drop rate")
                scanner_drop = Scanner(runner.run, maxrate_rate / 2)
                (status, step_cnt, nodrop, nodrop_rate) = scanner_drop.search(0.5, 0.01)
                l.info("Found for Client Count %d Max message Rate %d with no drop (%f)" %
                       (client_count, nodrop_rate, nodrop))
            else:
                nodrop_rate = rate

        # Delete all launched apps once the required drop is achieved for this set
        runner.delete_all_launched_apps()
        self.first_test.stop_appserver()
        l.info("TestSuite Completed.")
        sys.exit(0)


def Run(argv):  # NOQA
    usage = ('python %prog --c_pub --c_sub'
             ' --test_duration=<time to run test> --msg_batch=<msg burst batch before sleep>')
    parser = OptionParser(description='kafka scale maxrate test master',
                          version="0.1", usage=usage)
    parser.add_option("--test_duration", dest='test_duration', type='int', default=15)
    parser.add_option("--msg_batch", dest='msg_batch', type='int', default=100)
    parser.add_option("--config_file", dest='config_file', type='string', default='hydra.ini')
    (options, args) = parser.parse_args()

    RunSuitMaxRate(options)
    return True
