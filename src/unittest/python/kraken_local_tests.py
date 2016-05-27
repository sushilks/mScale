__author__ = 'AbdullahS'
from sys import path
path.append("src/main/python")

import unittest
import logging
import os
from pprint import pprint, pformat  # NOQA
from hydra.lib import util
from hydra.kraken.kraken import Kraken

l = util.createlogger('KrakenLocalTest', logging.INFO)


class KrakenLocalTest(unittest.TestCase):
    """
    Test class that attempts to unit test
    kraken functionality.
    Will have more things being added on as
    it matures.
    """
    def setUp(self):
        l.info("KrakenLocalTest initated")

    def test1(self):
        l.info("test1 launched")
        pwd = os.getcwd()
        l.info("CWD = " + pformat(pwd))

        def options():
            None
        setattr(options, 'test_duration', 10)
        setattr(options, 'config_file', pwd + '/src/unittest/python/test.ini')
        k = Kraken(options, runtest=False, mock=True)
        k.start_appserver()
        res = k.release_the_kraken()
        k.stop_appserver()
        print("RES = " + pformat(res))

        # Remove unittest process logs from live directory
        files = [f for f in os.listdir("./live") if f.endswith(".log")]
        for f in files:
            try:
                f_name = "./live/" + f
                l.debug("removing %s", f_name)
                os.remove(f_name)
            except:
                pass

if __name__ == '__main__':
    unittest.main()
