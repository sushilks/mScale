__author__ = 'AbdullahS'

import logging
from hydra.lib import util
from hydra.lib import common

l = util.createlogger('kraken_api', logging.INFO)
# l.setLevel(logging.DEBUG)


class KrakenApi(object):
    def __init__(self):
        l.info("Kraken_api initiated")

    def block_ip_port_on_node(self, ip_to_block, port, chain="INPUT", protocol="tcp", host_ip="", user=""):
        """
        Blocks all incoming communication from an ip on a host (local or remote)
        @args:
        ip_to_block:     IP to block
        port:            Port to block
        chain:           rule chain, INPUT, OUTPUT
        protocol:        tcp, udp
        host_ip:         Host to put this iptable rule on (Default executes on localhost)
        user:            Remote user

        """
        l.info("Attempting to block all communication from ip:port [%s:%s]", ip_to_block, port)
        # Block all incoming traffic from ip_to_block
        cmd = "sudo /sbin/iptables -A %s -p %s --destination-port %s -s %s -j DROP" % (chain, protocol, port, ip_to_block)
        if host_ip and user:
            common.execute_remote_cmd(host_ip, user, cmd)
        else:
            common.execute_local_cmd(cmd)

    def unblock_ip_port_on_node(self, ip_to_unblock, port, chain="INPUT", protocol="tcp", host_ip="", user=""):
        """
        Blocks all incoming communication from an ip on a host (local or remote)
        @args:
        ip_to_block:     IP to block
        port:            Port to block
        chain:           rule chain, INPUT, OUTPUT
        protocol:        tcp, udp
        host_ip:         Host to put this iptable rule on (Default executes on localhost)
        user:            Remote user
        """
        l.info("Attempting to UNblock all communication from ip:port [%s:%s]", ip_to_unblock, port)
        # Block all incoming traffic from ip_to_block
        cmd = "sudo /sbin/iptables -D %s -p %s --destination-port %s -s %s -j DROP" % (chain, protocol, port, ip_to_unblock)
        if host_ip and user:
            common.execute_remote_cmd(host_ip, user, cmd)
        else:
            common.execute_local_cmd(cmd)
