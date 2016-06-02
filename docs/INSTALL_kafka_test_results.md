
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

    jupyter notebook
    #Execute 'run tests & graph' block in notebook

**OTHER RELEVANT COMMANDS**

- How to Purge Kafka Queue

      bin/kafka-topics.sh --zookeeper 127.0.0.1:2181 --delete --topic default-topic

- Log Location:

        /opt/mesos/slaves/6bcaf7fb-bb8f-4912-aed9-7328597635d8-S0/frameworks/77dc7a7a-3cb7-45ae-9986-7695cba33d3d-0000/executors/g1_kafka-sub.75be999e-245e-11e6-82f3-42010a0a0050/runs/bb4b52dd-825f-410f-8b35-3f6292613083/src/main/scripts

 or direclty through the Mesos UI, following the path:

        Mesos/<App>/sandbox/stderr


## Kafka Configuration parameters

Two values are important (long polling):

- `fetch.min.bytes`: The broker will wait for this amount of data to fill BEFORE it sends the response to the consumer client.
- `fetch.wait.max.ms`: The broker will wait for this amount of time BEFORE sending a response to the consumer client, unless it has enough data to fill the response (fetch.message.max.bytes)

**PUBLISHER CONFIGURATION:**

- `batch_size` (given by test param `msg_batch`): This configuration parameter controls the default batch size in [bytes]. It is set to (average_message_length = 14) * (msg_batch)

- `acks` (externally configurable)
  - 1: wait for leader to write the record to its local log only.
  - 0:

- `linger_ms` = 5


**CONSUMER CONFIGURATION:**

- consumer.max_buffer_size=0
When subscribing to a topic with a high level of messages that have not been received before, the consumer/client can max out and fail.  Setting an infinite buffer size (zero) allows it to take everything that is available.

- group_id (different group id)
If all consumers use the same group id, messages in a topic are distributed among those consumers. In other words, each consumer will get a non-overlapping subset of the messages. Having more consumers in the same group increases the degree of parallelism and the overall throughput of consumption. See the next question for the choice of the number of consumer instances. On the other hand, if each consumer is in its own group, each consumer will get a full copy of all messages.

**BROKER CONFIGURTION**

1
2
log.retention.ms=5000
log.retention.check.interval.ms=10000
The first defines that the log is only kept for 5 seconds. The second that checks for logs to delete are done in 10s intervals. This was actually fun to find since mostly the documentation talks about using hours. Some mention doing it at very fine level of minutes.. But it is also possible to do in milliseconds as above. Again, I found that somewhere…:)

bin/kafka-topics.sh --zookeeper localhost:2181 --alter --topic default-topic --config retention.ms=5000 retention.check.interval.ms=10000

bin/kafka-topics.sh --zookeeper 127.0.0.1:2181 --alter --topic base-topic --config retention.ms=5000



## Relevant Links

- **Kafka**
    - https://cwiki.apache.org/confluence/display/KAFKA/Index
- **How to Install Kafka**
    -
- **Kafka Python Client**
    - https://github.com/dpkp/kafka-python

# Automated KAFKA-TEST for n-clients / x-message rate

The goal of this test is to stress the distributed messaging system **Apache Kafka** with increased client load. For this purpose, we increase ...

For these tests, we had two (2) google cloud instances each with the following specs:

- Machine Type: n1-standard-4 (4 vCPUs, 15 GB memory)
- CPU platform: Intel Ivy Bridge
- OS: Ubuntu 14.04
- Kernel: 3.19.0-59-generic

## Test Scenario

- Version: Kafka 0.9
- One (1) Broker
- One (1) Topic
- No replication
- Producers acks = 1 (i.e., wait for leader to write the record to its local log only.)

Scenario 1: ack = 1 (1: Wait for leader to write the record to its local log only.)

Scenario 2: ack = 0 (0: Producer will not wait for any acknowledgment from the server.)


```python
import sys
import time
from pprint import pprint, pformat  # NOQA
from hydra.kafkatest.runtest import RunTestKAFKA
```


```python
class Options():
    test_duration = 10
    msg_batch = 100        
    msg_rate= 2000
    total_sub_apps = 1
    config_file = 'hydra.ini'
    keep_running = False
```


```python
global_results = dict()
test_instance = None
options = Options()
runner = RunTestKAFKA(options, False)      #Initialize ALL variables (from CLI options and hydra.ini config file)
first_test = False
```


```python
def RunTest(test_name, first_test):
    if not first_test:
        runner.start_appserver()
        first_test = True
    else:
        runner.set_options(options)
        runner.scale_sub_app()
    res = runner.run_test()
    print("RES = " + pformat(res))
    if not options.total_sub_apps in global_results:
         global_results[options.total_sub_apps] = {}
    global_results[options.total_sub_apps][test_name] = res

```


```python
client_set = [10, 50, 300, 500]
msg_rate_set = [1000, 1500, 2000, 3000]
#client_set = [10]
#msg_rate_set = [1000, 2000]
first_test = False

for client_num in client_set:
    options.total_sub_apps = int(client_num / 10)
    for msg_rate in msg_rate_set:
        options.msg_rate = msg_rate
        RunTest(msg_rate, first_test)
        first_test = True
        time.sleep(5)
```


```python
import plotly.plotly as py
from plotly.graph_objs import *
import operator

traces_plot1 = []
traces_plot2 = []
traces_plot3 = []

for trace, tests_per_trace in global_results.iteritems():
    average_packet_loss = []
    average_packets = []
    average_rate = []
    average_tx_rate = []
    client_count = []
    failing_clients = []
    failing_clients_rate = []
    packet_tx = []
    pub_net_rxrate = []
    pub_net_txrate = []

    tests_sorted = sorted(tests_per_trace.items(), key=operator.itemgetter(0))

    for test in tests_sorted:
        average_packet_loss.append(test[1]['average_packet_loss'])
        average_packets.append(test[1]['average_packets'])
        average_rate.append(test[1]['average_rate'])
        average_tx_rate.append(test[1]['average_tx_rate'])            
        client_count.append(test[1]['client_count'])
        failing_clients.append(test[1]['failing_clients'])
        if test[1]['failing_clients'] != 0:            
            failing_clients_rate.append(test[1]['failing_clients_rate'])
        packet_tx.append(test[1]['packet_tx'])
        pub_net_rxrate.append(test[1]['pub_net_rxrate'])
        pub_net_txrate.append(test[1]['pub_net_txrate'])

    trace_plot1 = Scatter(
      x=average_tx_rate,
      y=average_rate,
      mode = 'lines+markers',
      name = 'client_count = ' + str(trace*10),
      line=dict(
        shape='spline'
        )
    )
    trace_plot2 = Scatter(
      x=average_tx_rate,
      y=average_packet_loss,
      mode = 'lines+markers',
      name = 'client_count = ' + str(trace*10),
      line=dict(
        shape='spline'
        )
    )
    trace_plot3 = Scatter(
      x=average_tx_rate,
      y=failing_clients_rate,
      mode = 'lines+markers',
      name = 'client_count = ' + str(trace*10),
      line=dict(
        shape='spline'
        )
    )

    traces_plot1.append(trace_plot1)
    traces_plot2.append(trace_plot2)
    traces_plot3.append(trace_plot3)


```

    /home/annyz/venv/local/lib/python2.7/site-packages/requests/packages/urllib3/util/ssl_.py:318: SNIMissingWarning: An HTTPS request has been made, but the SNI (Subject Name Indication) extension to TLS is not available on this platform. This may cause the server to present an incorrect TLS certificate, which can cause validation failures. You can upgrade to a newer version of Python to solve this. For more information, see https://urllib3.readthedocs.org/en/latest/security.html#snimissingwarning.
      SNIMissingWarning
    /home/annyz/venv/local/lib/python2.7/site-packages/requests/packages/urllib3/util/ssl_.py:122: InsecurePlatformWarning: A true SSLContext object is not available. This prevents urllib3 from configuring SSL appropriately and may cause certain SSL connections to fail. You can upgrade to a newer version of Python to solve this. For more information, see https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning.
      InsecurePlatformWarning



```python
data = Data(traces_plot1)
# Edit the layout
layout = dict(title = 'Average Client Rate',
              xaxis = dict(title = 'Average Tx Rate [pps]'),
              yaxis = dict(title = 'Average Rx Rate [pps]'),
              )

# Plot and embed in notebook
fig = dict(data=data, layout=layout)
py.iplot(fig, filename = 'kafka-rx-tx')
```

    /home/annyz/venv/local/lib/python2.7/site-packages/requests/packages/urllib3/util/ssl_.py:122: InsecurePlatformWarning:

    A true SSLContext object is not available. This prevents urllib3 from configuring SSL appropriately and may cause certain SSL connections to fail. You can upgrade to a newer version of Python to solve this. For more information, see https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning.


![ClientRate](images/Average_Rx1.png)


```python
data = Data(traces_plot2)
# Edit the layout
layout = dict(title = 'Average Packet Loss',
              xaxis = dict(title = 'Average Tx Rate [pps]'),
              yaxis = dict(title = 'Average Packet Loss [%]'),
              )

# Plot and embed in notebook
fig = dict(data=data, layout=layout)
py.iplot(fig, filename = 'kafka-loss-tx')
```

    /home/annyz/venv/local/lib/python2.7/site-packages/requests/packages/urllib3/util/ssl_.py:122: InsecurePlatformWarning:

    A true SSLContext object is not available. This prevents urllib3 from configuring SSL appropriately and may cause certain SSL connections to fail. You can upgrade to a newer version of Python to solve this. For more information, see https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning.


![ClientRate](images/average_packet_loss1.png)



```python
data = Data(traces_plot3)
# Edit the layout
layout = dict(title = 'Failing Clients Rate',
              xaxis = dict(title = 'Average Tx Rate [pps]'),
              yaxis = dict(title = 'Average Failing Clients Rate [pps]'),
              )

# Plot and embed in notebook
fig = dict(data=data, layout=layout)
py.iplot(fig, filename = 'kafka-fail-tx')
```

    /home/annyz/venv/local/lib/python2.7/site-packages/requests/packages/urllib3/util/ssl_.py:122: InsecurePlatformWarning:

    A true SSLContext object is not available. This prevents urllib3 from configuring SSL appropriately and may cause certain SSL connections to fail. You can upgrade to a newer version of Python to solve this. For more information, see https://urllib3.readthedocs.org/en/latest/security.html#insecureplatformwarning.




![ClientRate](images/failing_rate1.png)




```python
runner.delete_all_launched_apps()
runner.stop_appserver()
```
