
# HYDRA Scaling Test 3: Apache Kafka

## Test Goal

The goal of this test is to stress the distributed messaging system **Apache Kafka** with increased client load. The general setup is quite simple. A Kafka Producer sends records at a--maximum--pre-defined transmission rate to the Kafka Server (i.e., cluster) which holds on to these records and hands them out to consumer(s). In this test we assume the following considerations:

- One Broker.
- One Producer with configurable transmission rate.
- (N) Consumers (defined by user when launching the test).

## Requirements

- **Apache Kafka 0.9+**
  *Note: this version is required as *kafka-python* (Kafka Python Client) is best used with newer brokers (0.10 or 0.9).*
    - Java  
    - Zookeeper
- **Kafka Python Client** (kafka-python): to create Kafka producers & consumers.

  List of available Kafka Clients for most programming languages are available in the following link: https://cwiki.apache.org/confluence/display/KAFKA/Clients#Clients-For0.8.x


## High-Level Workflow

- Mesos, Marathon and Hydra (i.e., test environment) configuration parameters can be set in the INI file: `hydra.ini`
- Test-related configuration parameters can be specified by the user along the command line when launching the test, e.g., :

  `hydra kafka --total_sub_apps=20`

- `hydra/kafkatest/runtest.py` is the master python file for the Kafka Test.
- The test launches one (1) Publisher (*kafka-pub*) (PUB) and (*n*) Subscribers (*kafka-sub*) (SUB). The number of subscribers is defined when launching the test with the `--total_sub_apps` flag, which defaults to 100 when not specified.
- PUB and SUBs have a ZMQ REP (Reply) server to listen to signals and for data (stats) collection.


## Installation

The following needs to be done in each slave node (where the actual broker/producer/consumer(s) will be launched):

**STEP 1: INSTALL APACHE KAFKA**

  **1.1 Install Apache Kafka Requirements (Java & ZooKeeper)**

    echo "Install Apache Kafka (Broker)"
    echo "Update the list of available packages"
    sudo apt-get update
    echo "Install Apache Kafka requirement: Java runtime environment"
    sudo apt-get install default-jre
    echo "Install Apache Zookeeper: used by Kafka to detect failed nodes and elect leaders (among others)"
    sudo apt-get install zookeeperd
    echo "ZooKeeper daemon should start automatically, listening on port 2181"

  **1.2 Check Zookeeper Installation**

  To make sure that it is working, connect to it via Telnet:

    telnet localhost 2181

At the Telnet prompt, type in `ruok` and press ENTER. If everything's fine, ZooKeeper will say `imok` and end the Telnet session.

  **1.3 Install Apache Kafka**

    echo "Download and Extract Kafka Binaries"
    echo "Create Downloads dir to store downloads".
    mkdir -p ~/Downloads
    echo "Download Kafka binaries.""
    wget "http://mirror.cc.columbia.edu/pub/software/apache/kafka/0.8.2.1/kafka_2.11-0.8.2.1.tgz" -O ~/Downloads/kafka.tgz
    echo "Create a directory called kafka and change to this directory. This will be the base directory of the Kafka installation."
    mkdir -p ~/kafka && cd ~/kafka
    echo "Extract the archive"
    tar -xvzf ~/Downloads/kafka.tgz --strip 1


  **1.4 Configure the Kafka Server (Broker)**

    echo "Open server.properties"
    vim ~/kafka/config/server.properties
    echo "Enable the delete topics feature, which is disabled by default"

Add the following line at the end of the file:

    delete.topic.enable = true

  **1.5 Start the Kafka Server**

    echo "Run the kafka-server-start.sh script using nohup to start the Kafka server as a background process that is independent of your shell session."
    nohup ~/kafka/bin/kafka-server-start.sh ~/kafka/config/server.properties > ~/kafka/kafka.log 2>&1 &

You now have a Kafka server which is listening on port **9092**.

Link to Apache Kafka Installation:
 https://www.digitalocean.com/community/tutorials/how-to-install-apache-kafka-on-ubuntu-14-04


**STEP 2: INSTALL KAFKA PYTHON CLIENT**

    echo "Install Kafka Python Client"
    sudo pip install kafka-python

## Important Notes

- **Kafka dependency with Zookeeper**

Starting from 0.9, all the Zookeeper dependency from the clients has been removed. However, the brokers continue to be heavily depend on Zookeeper for:
- Server failure detection.
- Data partitioning.
- In-sync data replication.

## How to Run the Test?

### Execute Kafka Test

**MASTER**

    source ../venv/bin/activate
    cd hydra
    pip uninstall -y hydra && pyb install -x run_unit_tests && pyb install --verbose
    hydra kafka

### Execute Kafka Tests (batch)

**CLI**

    hydra kafka-batch

**IPython Notebook**

    jupyter notebook
    #Execute 'run tests & graph' block in notebook

**OTHER RELEVANT COMMANDS**

- How to Purge Kafka Queue

      bin/kafka-topics.sh --zookeeper 127.0.0.1:2181 --delete --topic <topic_name>

- Log Location:

        /opt/mesos/slaves/6bcaf7fb-bb8f-4912-aed9-7328597635d8-S0/frameworks/77dc7a7a-3cb7-45ae-9986-7695cba33d3d-0000/executors/g1_kafka-sub.75be999e-245e-11e6-82f3-42010a0a0050/runs/bb4b52dd-825f-410f-8b35-3f6292613083/src/main/scripts

 or direclty through the Mesos UI, following the path:

        Mesos/<App>/sandbox/stderr


## Kafka Configuration parameters

Two values are important (long polling):

- `fetch.min.bytes`: The broker will wait for this amount of data to fill BEFORE it sends the response to the consumer client.
- `fetch.wait.max.ms`: The broker will wait for this amount of time BEFORE sending a response to the consumer client, unless it has enough data to fill the response (fetch.message.max.bytes)

**PUBLISHER CONFIGURATION:**

- `batch_size` (given by test param `msg_batch`): This configuration parameter controls the default batch size in [bytes].

- `acks` (externally configurable)
  - 1: wait for leader to write the record to its local log only.
  - 0: don't wait for ack

- `linger_ms`


**CONSUMER CONFIGURATION:**

- consumer.max_buffer_size=0
When subscribing to a topic with a high level of messages that have not been received before, the consumer/client can max out and fail.  Setting an infinite buffer size (zero) allows it to take everything that is available.

- group_id (different group id)
If all consumers use the same group id, messages in a topic are distributed among those consumers. In other words, each consumer will get a non-overlapping subset of the messages. Having more consumers in the same group increases the degree of parallelism and the overall throughput of consumption. See the next question for the choice of the number of consumer instances. On the other hand, if each consumer is in its own group, each consumer will get a full copy of all messages.


## Relevant Links

- **Kafka**
    - https://cwiki.apache.org/confluence/display/KAFKA/Index
- **How to Install Kafka**
    - https://www.digitalocean.com/community/tutorials/how-to-install-apache-kafka-on-ubuntu-14-04
- **Kafka Python Client**
    - https://github.com/dpkp/kafka-python
