__author__ = 'AbdullahS'
from sys import path
path.append("src/main/python")

import unittest
import logging
import time
import socket
from pprint import pprint, pformat  # NOQA
from hydra.lib import util
from hydra.lib.hydrabase import HydraBase
from hydra.lib.utility.h_threading import HThreading

l = util.createlogger('RuntestLocalTest', logging.INFO)


class RuntestLocalTest(unittest.TestCase):
    """
    Test class that attempts to unit test
    kraken functionality.
    Will have more things being added on as
    it matures.
    """
    def setUp(self):
        l.info("LocalTest initialized")

    def test_ip_block(self):
        l.info("test ip block launched")
        self.TCP_IP = '127.0.0.1'
        self.TCP_PORT = 5005
        self.BUFFER_SIZE = 5
        self.t_exceptions = []
        self.h_threading = HThreading()
        self.k_api = HydraBase
        self.pkts_dropped = 0  # loose count, not 100% accurate
        self.pkts_received = 0
        self.stop = False
        self.server_ready = False

        def thread_cb(t_exceptions):
            for exception in t_exceptions:
                self.t_exceptions.append(exception)
                l.error(exception)

        def sender():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((self.TCP_IP, self.TCP_PORT))
            s.listen(1)
            msg = "Pong!"
            self.server_ready = True
            conn, addr = s.accept()
            l.debug('Connection address:', addr)
            while True:
                if self.stop:
                    break
                data = conn.recv(self.BUFFER_SIZE)
                if not data:
                    break
                l.debug("SENDER: received data:", data)
                conn.send(msg)
            conn.close()

        def receiver():
            msg = "Ping!"
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.TCP_IP, self.TCP_PORT))
            s.setblocking(0)
            while True:
                if self.stop:
                    break
                s.send(msg)
                try:
                    data = s.recv(self.BUFFER_SIZE)
                except socket.error:
                    l.debug("socket error")
                    self.pkts_dropped += 1
                    time.sleep(0.2)
                    continue
                l.debug("RECEIVER: received data:", data)
                time.sleep(0.5)
                if data == "Pong!":
                    self.pkts_received += 1
            s.close()

        # Start sender, receiver in threads
        self.h_threading.start_thread(thread_cb, sender)
        t_st = time.time()
        while not self.server_ready:
            if (time.time() - t_st) > 5:
                raise Exception("Timed out waiting to start server")
            continue
        self.h_threading.start_thread(thread_cb, receiver)

        l.info("Waiting for Atleast 5 packets to be received")
        timeout = 10
        t_st = time.time()
        while self.pkts_received < 5:
            if (time.time() - t_st) > timeout:
                raise Exception("Timed out waiting for pkts_recieved counter")
            continue
        curr_pkt_count = self.pkts_received

        l.info("Atleast 5 packets received, proceeding with putting in iptable rule")
        self.k_api.block_ip_port_on_node(self.TCP_IP, self.TCP_PORT, chain="INPUT", protocol="tcp")

        l.info("Waiting for at least 10 dropped packets")
        t_st = time.time()
        while self.pkts_dropped < 10:
            if (time.time() - t_st) > timeout:
                raise Exception("Timed out waiting for pkts_dropped counter")
            continue

        l.info("Atleast 10 packets dropped successfully, deleting iptable rule")
        self.k_api.unblock_ip_port_on_node(self.TCP_IP, self.TCP_PORT, chain="INPUT", protocol="tcp")
        t_st = time.time()
        timeout = 10
        while self.pkts_received < curr_pkt_count + 5:
            if (time.time() - t_st) > timeout:
                raise Exception("Timed out waiting for pkts_recieved counter")
            continue
        l.info("Successfully deleted iptable rule")
        self.stop = True
        self.h_threading.join_all()


if __name__ == '__main__':
    unittest.main()
