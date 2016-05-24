#!/bin/bash

# ZooKeeper will be pulled in and installed as a dependency automatically.
# The slaves do not require to run their own zookeeper instances
sudo service zookeeper stop
sudo bash -c "echo manual | sudo tee /etc/init/zookeeper.override"
# make sure the Mesos master process doesn't start on our slave servers.
sudo bash -c "echo manual | sudo tee /etc/init/mesos-master.override"
sudo service mesos-master stop


