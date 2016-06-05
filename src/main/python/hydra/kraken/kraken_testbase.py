__author__ = 'AbdullahS'

from pprint import pprint, pformat  # NOQA
import logging
from hydra.lib import util
from hydra.kraken.kraken_api import KrakenApi

l = util.createlogger('krakenTestBase', logging.INFO)
# l.setLevel(logging.DEBUG)


class KrakenTestBase(object):
    """
    Base KrakenTestBase class. Expected to hold
    any common Kraken test methods pertaining to getting
    info from underlying hydra layer.
    All DB/other Test classes are expected to derive from this.
    """
    def __init__(self, name, h_han):
        l.info("KrakenTestBase: Launching Test[%s]", name)
        self.name = name
        self.k_api = KrakenApi()
        self.h_han = h_han  # Hydra handle, makes hydra lib API accessible here

    def get_slave_attr(self):
        """
        Get all slave attributes
        """
        self.attr_list = []
        for idx, info in self.h_han.mesos_cluster.items():
            self.attr_list.append(info["match"])
        return self.attr_list

    def prep_iplist_with_attr(self):
        """
        Get all slave ips corresponding to attributes.
        Returns a comma seprated list
        """
        self.ip_list = []
        self.attr_list = self.get_slave_attr()
        for attr in self.attr_list:
            slave_ip = self.h_han.get_mesos_slave_ip_attr(attr)
            self.ip_list.append(slave_ip)
        return ",".join(self.ip_list)

    def launch_db(self):
        """
        Implement this in your TestClass
        """
        pass
