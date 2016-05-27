__author__ = 'AbdullahS'

from pprint import pprint, pformat   # NOQA
import logging
from hydra.lib import util
from hydra.lib.utility.py_sys_cmd import PySysCommand

l = util.createlogger('h_common', logging.INFO)
# l.setLevel(logging.DEBUG)


def execute_remote_cmd(ip, user, cmd, timeout=10, suppress_output=False):
    """
    Execute a remote command via ssh
    @args:
    ip:              Remote IP to execute command on
    user:            Remote user
    cmd:             Command to execute
    timeout:         Command timeout
    supress_output:  Whether to dump stdout

    """
    cmd = "ssh -o StrictHostKeyChecking=no %s@%s \"%s\"" % (user, ip, cmd)
    l.info("Executing remote command [%s] on ip[%s], user[%s]", cmd, ip, user)
    pg_cmd = PySysCommand(cmd)
    pg_cmd.run(timeout=timeout)
    output = pg_cmd.stdout + pg_cmd.stderr
    if not suppress_output:
        l.info("Result: %s", output)
    return output


def execute_local_cmd(cmd, timeout=10):
    """
    Execute a local command
    @args:
    cmd:             Command to execute
    timeout:         Command timeout

    """
    l.info("Executing local command [%s]", cmd)
    pg_cmd = PySysCommand(cmd)
    pg_cmd.run(timeout=timeout)
    output = pg_cmd.stdout + pg_cmd.stderr
    l.info("Result: %s", output)
