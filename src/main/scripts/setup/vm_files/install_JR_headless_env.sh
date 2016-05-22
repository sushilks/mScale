#!/bin/bash
sudo add-apt-repository -y ppa:webupd8team/java
echo debconf shared/accepted-oracle-license-v1-1 select true | sudo debconf-set-selections
echo debconf shared/accepted-oracle-license-v1-1 seen true | sudo debconf-set-selections
sudo apt-get -y update
sudo apt-get -y install oracle-java8-installer
sudo apt-get -y install oracle-java8-set-default
