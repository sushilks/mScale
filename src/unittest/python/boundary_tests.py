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
        if self.verbose:
            pprint(" RANGE = " + pformat(range) + " VAL = " + pformat(val))
        self.set_expected_responsefn(range, lambda x: val)

    def set_expected_responsefn(self, range, fn):
        self.exp_value[range] = fn

    def generate(self, val):
        # find the closest value to val in exp_val
        if self.verbose:
            print('---')
        fn = self.exp_value[max(k for k in self.exp_value if k <= val)]
        res = fn(val)
        if self.verbose:
            print('moc1 called with ' + pformat(val) + " Resp:" + pformat(res))
        return (True, val, res)

    def run_for_exp(self, test, start_dt, exp_step_correction, exp_data, perr):
        self.set_expected_response(start_dt, 1)
        (status, step_cnt, res_err, res) = test.scanner.search(0, perr)
        est = math.log(start_dt, 2) + test.scanner.inital_toggle_count + exp_step_correction
        if self.verbose:
            print("RESULT = %d/%d" % (res, start_dt) + " after %d/%d steps" %
                  (step_cnt, test.scanner.inital_toggle_count) +
                  " exp_cnt = %f exp_data %d" % (est, exp_data))
        est = int(est) - 1
        test.assertEqual(step_cnt, est)
        test.assertEqual(int(res + 0.5), exp_data)
        test.assertEqual(status, True)


class ScannerUnitTest(unittest.TestCase):
    def setUp(self):
        self.mocgen = MocGen()
        self.scanner = Scanner(self.mocgen.generate, 1000)

    def test1(self):
        dt = 12345
        self.mocgen.run_for_exp(self, dt, 1, dt, 0.0001)

    def test2(self):
        dt = 2345
        self.mocgen.run_for_exp(self, dt, 0, 2344, 0.001)

    def test3(self):
        dt = 345
        self.mocgen.run_for_exp(self, dt, 2, 344, 0.01)

    def test4(self):
        dt = 99999
        self.mocgen.run_for_exp(self, dt, -2, 99992, 0.0001)

    def test5(self):
        dt = 1024
        self.mocgen.run_for_exp(self, dt, 1, 1023, 0.001)

    def test6(self):
        dt = 128
        self.mocgen.run_for_exp(self, dt, 4, dt, 0.01)

    def test7(self):
        dt = 2000
        self.mocgen.run_for_exp(self, dt, 0, 1998, 0.001)

    def test8(self):
        dt = 3000
        self.mocgen.run_for_exp(self, dt, 0, 2998, 0.001)

    def test9(self):
        self.mocgen.set_expected_response(10000, 1)
        self.mocgen.set_expected_response(12012, 10)
        self.mocgen.set_expected_response(13120, 20)
        perr = 0.001
        (sts, step_cnt, res_err, res) = self.scanner.search(0, perr)
        self.assertEqual(step_cnt, 14)
        res = int(res + 0.5)
        self.assertEqual(res, 9992)
        (sts, step_cnt, res_err, res) = self.scanner.search(1, perr)
        self.assertEqual(step_cnt, 14)
        res = int(res + 0.5)
        self.assertEqual(res, 12008)
        (sts, step_cnt, res_err, res) = self.scanner.search(5, perr)
        self.assertEqual(step_cnt, 14)
        res = int(res + 0.5)
        self.assertEqual(res, 12008)
        (sts, step_cnt, res_err, res) = self.scanner.search(15, 0.0001)
        res = int(res + 0.5)
        self.assertEqual(res, 13120)
        self.assertEqual(step_cnt, 17)

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
        (sts, step_cnt, res_err, res) = self.scanner.search(15, 0.001)
        # pprint("----> step_cnt %d res %d" % (step_cnt, res))
        self.assertEqual(step_cnt, 14)
        self.assertTrue(abs(res - 9994) < 100)
        (sts, step_cnt, res_err, res) = self.scanner.search(5, 0.0001)
        # pprint("----> step_cnt %d res %d" % (step_cnt, res))
        self.assertEqual(step_cnt, 14)
        self.assertTrue(abs(res - 994) < 100)

    def test11(self):
        return True
        data = [(500, 979, 0.0), (1000, 1016, 0.0), (2000, 2014, 0.0), (4000, 4013, 0.0),
                (8000, 8009, 0.0), (16000, 16005, 0.0), (32000, 23077, 14.49),
                (24000, 23957, 0.18), (28000, 24188, 13.17), (26000, 24570, 4.88),
                (27000, 24521, 8.92), (27500, 27357, 0.0), (27750, 26011, 5.54),
                (27875, 27606, 0.97), (27937, 26301, 4.4)]

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
        (sts, step_cnt, res_err, res) = self.scanner.search(15)
        # pprint("----> step_cnt %d res %d" % (step_cnt, res))
        self.assertEqual(step_cnt, 16)
        self.assertTrue(abs(res - 9994) < 100)
        (sts, step_cnt, res_err, res) = self.scanner.search(5)
        # pprint("----> step_cnt %d res %d" % (step_cnt, res))
        self.assertEqual(step_cnt, 9)
        self.assertTrue(abs(res - 994) < 100)
        pprint(pformat(data))


if __name__ == '__main__':
    unittest.main()
