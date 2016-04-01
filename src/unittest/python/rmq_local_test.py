__author__ = 'AbdullahS'
from sys import path
path.append("src/main/python")

import unittest
import math
import random
import logging
import os
from pprint import pprint, pformat  # NOQA
from hydra.lib import util
from hydra.rmqtest.runtest import RunTestRMQ

l = util.createlogger('RMQLocalTest', logging.INFO)

class RMQLocalTest(unittest.TestCase):
    def setUp(self):
        l.info("RMQLocalTest initated")

    def test1(self):
        l.info("test1 launched")
        pwd = os.getcwd()
        l.info("CWD = " + pformat(pwd))

        def options():
            None
        #setattr(options, 'test_duration', 30)
        setattr(options, 'test_duration', 10)
        setattr(options, 'msg_batch', 50)
        setattr(options, 'msg_rate', 1000)
        setattr(options, 'config_file', pwd + '/hydra.ini')
        r = RunTestRMQ(options, False)
        r.start_appserver()
        res = r.run_test()
        raw_input("-------------------------------")
        r.delete_all_launched_apps()
        #print("RES = " + pformat(res))
        #if not options.keep_running:
        #    r.stop_appserver()
        #else:
        #    print("Keep running is set: Leaving the app server running")
        #    print("   you can use the marathon gui/cli to scale the app up.")
        #    print("   after you are done press enter on this window")
        #    input('>')
        #r.stop_appserver()


if __name__ == '__main__':
    unittest.main()
