__author__ = 'sushil'

import subprocess
import signal
import sys
import time
import atexit
import psutil
import logging
from hydra.lib import util

l = util.createlogger('cmgr', logging.INFO)


class ChildManager(object):
    def __init__(self, sighandler=True):
        if sighandler:
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

    def launch_children(self, ports=None):
        for name in self.jobs:
            if self.jobs[name]['running']:
                l.info("job [%s] already running", name)
                continue
            self.jobs[name]['fout'] = open('./' + name + '.stdout.log', 'w+')
            self.jobs[name]['ferr'] = open('./' + name + '.stderr.log', 'w+')
            self.jobs[name]['pid'] = None
            self.jobs[name]['process'] = subprocess.Popen(args=self.jobs[name]['cmd'],
                                                          cwd=self.jobs[name]['cwd'],
                                                          env=self.jobs[name]['env'],
                                                          stdout=self.jobs[name]['fout'],
                                                          stderr=self.jobs[name]['ferr'],
                                                          close_fds=True)
            self.jobs[name]['pid'] = self.jobs[name]['process'].pid
            if ports:
                self.jobs[name]['ports'] = ports
            atexit.register(self.jobs[name]['process'].terminate)
            self.jobs[name]['running'] = True

    def check_children(self):
        l.debug("Waiting for launched CHILD")
        while True:
            time.sleep(1)
        self.done = True
        l.debug("LAUNCH CHILD RETURNED")

    def done(self):
        return self.taskdone

    def wait(self):
        while True:
            if self.done():
                break
            time.sleep(1)

    def terminate_process_and_children(self, name):
        """
        Recursively terminate all children of
        respective process
        @args:
        name:   Name of the job
        """
        if name not in self.jobs:
            print("[%s] does not exist as a process!", name)
        ppid = self.jobs[name]['process'].pid
        try:
            parent_proc = psutil.Process(ppid)
        except psutil.NoSuchProcess:
            return
        children = parent_proc.children(recursive=True)
        for proc in children:
            l.debug(proc)
            try:
                proc.send_signal(signal.SIGKILL)
            except:
                pass
