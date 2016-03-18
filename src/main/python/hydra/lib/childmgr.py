__author__ = 'sushil'

import subprocess
import signal
import sys
import time
import atexit


class ChildManager(object):
    def __init__(self):
        signal.signal(signal.SIGCHLD, self.sigchild)
        self.taskdone = False
        self.jobs = {}

    def sigchild(self, signum, frame):
        print("Received SIGCHILD parent will exit as well")
        for name in self.jobs:
            if 'fout' in self.jobs[name]:
                self.jobs[name]['fout'].close()
                self.jobs[name]['ferr'].close()
        self.taskdone = True
        sys.exit(0)

    def add_child(self, name, cmd, wdir=None, env=None):
        if name in self.jobs:
            raise Exception('Name %s is already scheduled to launch' % name)
        self.jobs[name] = {
            'cmd': cmd,
            'cwd': wdir,
            'env': env,
            'running': False
        }

    def launch_children(self):
        for name in self.jobs:
            self.jobs[name]['fout'] = open('./' + name + '.stdout.log', 'w+')
            self.jobs[name]['ferr'] = open('./' + name + '.stderr.log', 'w+')
            self.jobs[name]['process'] = subprocess.Popen(args=self.jobs[name]['cmd'],
                                                          cwd=self.jobs[name]['cwd'],
                                                          env=self.jobs[name]['env'],
                                                          stdout=self.jobs[name]['fout'],
                                                          stderr=self.jobs[name]['ferr'],
                                                          close_fds=True)
            atexit.register(self.jobs[name]['process'].terminate)
            self.jobs[name]['running'] = True

    def check_children(self):
        print("Waiting for launched CHILD")
        while True:
            time.sleep(1)
        self.done = True
        print("LAUNCH CHILD RETURNED")

    def done(self):
        return self.taskdone

    def wait(self):
        while True:
            if self.done():
                break
            time.sleep(1)
