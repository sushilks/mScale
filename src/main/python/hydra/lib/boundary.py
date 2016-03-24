__author__ = 'sushil'

# A class to do binary search and tune one
# parameter.
import logging
from pprint import pprint, pformat  # NOQA
from hydra.lib import util

l = util.createlogger('runTestSuit', logging.INFO)
# l.setLevel(logging.DEBUG)


class Scanner(object):
    def __init__(self, runfunction, starting_value, search_approx=2):
        self.start_value = starting_value
        self.runfn = runfunction
        self.threshold = search_approx

    def search(self, expected_result):
        value = self.start_value
        inc = 0
        last_increase = value
        first_toggle = False
        cnt = 0
        self.inital_toggle_count = 0
        status = True
        while True:
            (status, rate, res) = self.runfn(value)
            if not status:
                break
            if res <= expected_result:
                if not first_toggle:
                    # aggressively increase in the begining
                    inc = value
                else:
                    # Once an area is found do search
                    inc = abs(1.0 * last_increase / 2)
            else:
                inc = -1 * abs(1.0 * last_increase / 2)
                first_toggle = True
            # pprint(" Iteration %d ::" % cnt + " value = %d res = %d inc = %f" % (value, res, inc) +
            #       " :: last_increase = %d" % last_increase)
            if abs(last_increase) < self.threshold:
                break
            last_increase = inc
            value += inc
            cnt += 1
            if not first_toggle:
                self.inital_toggle_count += 1
        return (status, cnt, int(value))

    def find_max_rate(self):
        value = self.start_value
        while True:
            (status, rate, drop) = self.runfn(value)
            if rate < value * 0.7:
                # max rate is likely rate
                break
            value += value
        return (True, rate, drop)

    def range(self, data):
        res = {}
        for r in data:
            l.info(self.runfn)
            res[r] = self.runfn(r)
        return res


class BoundaryRunnerBase(object):
    def __init__(self):
        pass

    def boundary_setup(self, options, arg1name, resfn):
        self.boundary_options = options
        self.boundary_arg1name = arg1name
        self.boundary_run_result = {}
        self.boundary_first_run = False
        self.boundary_resfn = resfn

    def boundary_run(self, arg1):
        l.info("Starting run with %s = %d" % (self.boundary_arg1name, arg1))
        if arg1 in self.boundary_run_result:
            res = self.boundary_run_result[arg1]
        else:
            setattr(self.boundary_options, self.boundary_arg1name, arg1)
            if not self.boundary_first_run:
                res = self.run_test(True)
                self.boundary_first_run = True
            else:
                # Update existing PUB and SUBs instead of launching new
                options = self.boundary_options
                setattr(options, self.boundary_arg1name, arg1)
                res = self.rerun_test(self.boundary_options)
            l.info("** AFTER RE RUN, SHOULD BE TRUE  **")
            l.info(self.boundary_first_run)
            self.boundary_run_result[arg1] = res
        return self.boundary_resfn(self.boundary_options, res)

    def run(self, arg1):
        return self.boundary_run(arg1)

    def run_test(self):
        print('this method needs to be implemented in the inherited class')
        assert(False)

    def rerun_test(self):
        print('this method needs to be implemented in the inherited class')
        assert(False)
