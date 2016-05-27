#!/bin/bash
sudo service mesos-slave stop || true
sudo bash -c "echo 'manual' > /etc/init/mesos-slave.override"
sudo service zookeeper stop || true
sudo service zookeeper start
sudo service mesos-master stop || true
sudo service mesos-master start
sudo service marathon stop  || true
sudo service marathon start
