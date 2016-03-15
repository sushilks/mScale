__author__ = 'sushil'
from sys import path
path.append("src/main/python")

import unittest
import math
import random
from pprint import pprint, pformat  # NOQA
from hydra.lib.boundary import Scanner


class MocGen(object):
    def __init__(self):
        self.exp_value = {}
        self.exp_value[0] = lambda x: 0
        self.verbose = False

    def set_expected_response(self, range, val):
        self.set_expected_responsefn(range, lambda x: val)

    def set_expected_responsefn(self, range, fn):
        self.exp_value[range] = fn

    def generate(self, val):
        # find the closest value to val in exp_val
        fn = self.exp_value[max(k for k in self.exp_value if k <= val)]
        res = fn(val)
        if self.verbose:
            print('moc1 called with ' + pformat(val) + " Resp:" + pformat(res))
        return (True, res)

    def run_for_exp(self, test, start_dt, exp_step_correction, exp_data):
        self.set_expected_response(start_dt, 1)
        (status, step_cnt, res) = test.scanner.search(0)
        est = math.log(start_dt, 2) + test.scanner.inital_toggle_count + exp_step_correction
        # print("RESULT = %d/%d" % (res, start_dt) + " after %d/%d steps" %
        # (step_cnt, test.scanner.inital_toggle_count) +
        #      " exp_cnt = %f exp_data %d" % (est, exp_data))
        est = int(est)
        test.assertEqual(step_cnt, est)
        test.assertEqual(res, exp_data)
        test.assertEqual(status, True)


class ScannerUnitTest(object):
    def setUp(self):
        self.mocgen = MocGen()
        self.scanner = Scanner(self.mocgen.generate, 1000, 2)

    def test1(self):
        dt = 12345
        self.mocgen.run_for_exp(self, dt, 0, dt)

    def test2(self):
        dt = 2345
        self.mocgen.run_for_exp(self, dt, 0, dt)

    def test3(self):
        dt = 345
        self.mocgen.run_for_exp(self, dt, 2, dt)

    def test4(self):
        dt = 99999
        self.mocgen.run_for_exp(self, dt, -1, 99994)

    def test5(self):
        dt = 1024
        self.mocgen.run_for_exp(self, dt, 0, 1023)

    def test6(self):
        dt = 128
        self.mocgen.run_for_exp(self, dt, 3, dt)

    def test7(self):
        dt = 2000
        self.mocgen.run_for_exp(self, dt, -1, 1994)

    def test8(self):
        dt = 3000
        self.mocgen.run_for_exp(self, dt, -1, 2994)

    def test9(self):
        self.mocgen.set_expected_response(10000, 1)
        self.mocgen.set_expected_response(12012, 10)
        self.mocgen.set_expected_response(13120, 20)
        (sts, step_cnt, res) = self.scanner.search(0)
        self.assertEqual(step_cnt, 16)
        self.assertEqual(res, 9994)
        (sts, step_cnt, res) = self.scanner.search(1)
        self.assertEqual(step_cnt, 17)
        self.assertEqual(res, 12011)
        (sts, step_cnt, res) = self.scanner.search(5)
        self.assertEqual(step_cnt, 17)
        self.assertEqual(res, 12011)
        (sts, step_cnt, res) = self.scanner.search(15)
        self.assertEqual(step_cnt, 17)
        self.assertEqual(res, 13119)

    def test10(self):
        def tfn1(val):
            # create a random function
            r = random.randint(10, 100)
            if (val + r) > 1000:
                return 10
            return 0

        def tfn2(val):
            # create a random function
            r = random.randint(10, 500)
            if (val + r) > 10000:
                return 20
            return 10
        self.mocgen.set_expected_responsefn(1000, tfn1)
        self.mocgen.set_expected_responsefn(10000, tfn2)
        (sts, step_cnt, res) = self.scanner.search(15)
        # pprint("----> step_cnt %d res %d" % (step_cnt, res))
        self.assertEqual(step_cnt, 16)
        self.assertTrue(abs(res - 9994) < 100)
        (sts, step_cnt, res) = self.scanner.search(5)
        # pprint("----> step_cnt %d res %d" % (step_cnt, res))
        self.assertEqual(step_cnt, 9)
        self.assertTrue(abs(res - 994) < 100)


if __name__ == '__main__':
    unittest.main()
