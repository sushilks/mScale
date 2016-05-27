__author__ = 'AbdullahS'

import logging
from hydra.lib import util
from hydra.lib import common

l = util.createlogger('kraken_api', logging.INFO)
# l.setLevel(logging.DEBUG)


class KrakenApi(object):
    def __init__(self):
        l.info("Kraken_api initiated")

    def block_ip_on_node(self, ip_to_block, host_ip="", user=""):
        """
        Blocks all incoming communication from an ip on a host (local or remote)
        @args:
        ip_to_block:     IP to block
        host_ip:         Host to put this iptable rule on (Default executes on localhost)
        user:            Remote user

        """
        l.info("Attempting to block all communication from ip [%s]", ip_to_block)
        # Block all incoming traffic from ip_to_block
        cmd = "sudo /sbin/iptables -I INPUT -s %s -j DROP" % (ip_to_block)
        if host_ip and user:
            common.execute_remote_cmd(host_ip, user, cmd)
        else:
            common.execute_local_cmd(cmd)

    def unblock_ip_on_node(self, ip_to_unblock, host_ip="", user=""):
        """
        UNBlocks all incoming communication from an ip on a host (local or remote)
        @args:
        ip_to_unblock:     IP to unblock
        host_ip:         Host to put this iptable rule on (Default executes on localhost)
        user:            Remote user

        """
        # Block all incoming traffic from ip_to_block
        l.info("Attempting to unblock all communication from ip [%s]", ip_to_unblock)
        cmd = "sudo /sbin/iptables -D INPUT -s %s -j DROP" % (ip_to_unblock)
        if host_ip and user:
            common.execute_remote_cmd(host_ip, user, cmd)
        else:
            common.execute_local_cmd(cmd)
