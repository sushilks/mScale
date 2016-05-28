#!/bin/bash

# Marathon configuration directory structure we need is not created automatically.
# We will have to create the directory and then we can copy the file over.
sudo mkdir -p /etc/marathon/conf
# Next, we need to define the list of zookeeper masters that Marathon will connect to for information and scheduling.
# This is same zookeepr connection string which we we used for Mesos. So, just copy that.
# This will allow our Marathon service to connect to the Mesos cluster.
sudo cp /etc/mesos-master/hostname /etc/marathon/conf
# define the list of zookeeper masters that Marathon will connect to for information and scheduling.
# This is the same zookeeper connection string that we've been using for Mesos
# This will allow our Marathon service to connect to the Mesos cluster
sudo cp /etc/mesos/zk /etc/marathon/conf/master

# we also want Marathon to store its own state information in zookeeper. For this, we will use the other
# zookeeper connection file as a base, and just modify the endpoint
sudo cp /etc/marathon/conf/master /etc/marathon/conf/zk
sudo sed -i 's/mesos/marathon/g' /etc/marathon/conf/zk
