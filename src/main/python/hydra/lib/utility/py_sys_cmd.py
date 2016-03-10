import subprocess
import threading
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

    def run(self, timeout=10, no_assert=False):
        def target():
            """
            subprocess.Popen wrapper that takes care of the dirty business of
            child processes spawned within the shell
            """
            self.process = subprocess.Popen([self.exec_cmd], stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
            self.stdout, self.stderr = self.process.communicate()
            self.cmd_status = self.process.returncode
        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive() and self.process:
            # Timeout occured, kill all group processes
            os.killpg(self.process.pid, signal.SIGTERM)
            time.sleep(2)
            if self.process.poll() is None:  # Force kill if still alive
                time.sleep(3)
                os.killpg(self.process.pid, signal.SIGKILL)
            thread.join()
            self.cmd_timeout = True
        # If Command failed or timedout
        if not no_assert:
            if (self.cmd_status != 0 or self.cmd_timeout):
                raise Exception("Command \'%s\' failed with out[%s], err [%s]" %
                                (self.exec_cmd, self.stdout, self.stderr))
