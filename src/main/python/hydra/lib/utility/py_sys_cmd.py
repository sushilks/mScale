import sys
from optparse import OptionParser
import subprocess
import threading
import json
import os
import signal
import time

class PySysCommand(object):
    """
    PySysCommand class wraps around subprocess Poopen,
    calls it in a thread to be able to timeout
    args:
    exec_cmd --- (required)   command string to execute
                              example = "mkdir -p /tmp/ghost"
    """
    def __init__(self, exec_cmd):
        self.exec_cmd = exec_cmd
        self.process = None
        self.cmd_timeout = False
        self.stdout = None
        self.stderr = None
        self.cmd_status = None

    def run(self, timeout=10, no_assert=False, pass_status=0, do_not_buffer_output=False):
        def target():
            """
            subprocess.Popen wrapper that takes care of the dirty business of
            child processes spawned within the shell
            """
            if self.do_not_buffer_output:
                self.process = subprocess.Popen([self.exec_cmd], shell=True, preexec_fn=os.setsid)
                self.process.communicate()
            else:
                self.process = subprocess.Popen([self.exec_cmd], stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
                self.stdout, self.stderr = self.process.communicate()
            self.cmd_status = self.process.returncode
        # this optional flag is useful when no output buffering is desired (e.g. for debugging scripts)
        self.do_not_buffer_output = do_not_buffer_output
        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive() and self.process:
            #print 'Timeout occured Terminating process'
            # Timeout occured, kill all processes in the group
            os.killpg(self.process.pid, signal.SIGTERM)
            time.sleep(2)
            if self.process.poll() is None:  # Force kill if process is still alive
                time.sleep(3)
                os.killpg(self.process.pid, signal.SIGKILL)
            thread.join()
            self.cmd_timeout = True
        # If Command failed or timedout
        if not no_assert:
            if (self.cmd_status != pass_status or self.cmd_timeout):
                raise Exception("Command \'%s\' failed with output [%s], error [%s]" % (self.exec_cmd, self.stdout, self.stderr))
