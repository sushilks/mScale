# ZMQ Client scale testing.

The initial setup is up an running, now it's possible to spawn thousands of clients. 
The test bed is written in a way that all the results here can be re-produced easily on any cloud or physical setup. 
For all our testing we are using google compute cloud.

We are still fixing bugs in the infra so the results are not final and will be updated for re-runs.

## Test 1 : Pub-Sub 
This test is designed to primarily validate the hydra architecture while testing python zmq performance at scale.
The pattern is from one publisher to many subscribers. We are checking the packet rate performance as the number of 
subscribers change.

### Test setup 
This involved 5 servers on google cloud
1 server (n1-standard-4) was dedicated to marathon-master/zookeeper etc.
1 server (n1-standard-4) was dedicated to running zmq-pub
3 servers(n1-standard-16) where dedicated for running zmq-sub

OS: Ubuntu 14.04
Kernel: 3.19.0-51-generic
Python version : 2.7.5
Zmq Version : 4.1.4

### Command line 
`>hydra zmqrate`

### Test methodology 
The test orchestrates the launch of publisher and the subscriber jobs on mesos cluster, (they are executed
as processes on the nodes. Not using any containers)
Once the process are up and running the test triggers the publisher to send different rate of traffic for 60 seconds. 
After the time interval rates are measured across all the subscribers and averaged. 
We keep increasing the rate till the publisher can not see any more increase and log it as the max rate. 

### Results
Table showing results on client count and message rate (Packets Per Second). Likely the packets are minimum size.

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=1193589650&format=image">


Here is a graph showing the maximum rate of message received at the subscribers as a function of number of clients.

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=971303165&format=image">

This chart is showing packet drops with increase in the number of clients.

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=632762905&format=image">

At 10k clients the python publisher was having problem responding to commands and calls where timing out, so there is 
no data gathered at that sample. 

It's interesting to note that the packet drop rate spikes up at around 80 clients and then drops down.
Zmq does the replication of packets at the source, so for every additional client the publisher has to copy and 
send the packet. i.e. the number of packet send by publisher = number of clients * rate of packets being send by application.
The last column on the table shows this number under "Publisher Packet Rate", varies around 2.5Mpps. 
The publisher packet rate is almost linear for all the samples. 

We did notice some anomaly around 80 client range with packet drops rate that's unexpected, On repeated runs 
it was notices that the amount of drops varied across different runs however the drop was always there.
The cpu usages during these experiments always peeked with PUB using ~200%. 
The publisher node had a network bandwidth usage of around 50~70MBps for the duration of the tests.

I am suspecting that the drop is correlated to amount of cpu that's available between the python and the zmq libraries,
 as the rate is changed on the transmit side the availability of the cpu also shifts causing the drop to show up. This 
 theory can be validated by putting together a C version of the PUB/SUB. We will do that next. 
 
 In any case the python results are useful for python implementations as around 80 client range there can be some drop 
  expected when pushing packets out at max rate.
  

For this the command line is
`>hydra zmqrate`


test


## Notes
Add additional test cases to measure here
