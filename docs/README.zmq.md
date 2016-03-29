# ZMQ Client scale testing.

The initial setup is up an running, now it's possible to spawn thousands of clients. 
The test bed is written in a way that all the results here can be re-produced easily on any cloud or physical setup. 
For all our testing we are using google compute cloud.

We are still fixing bugs in the infra so the results are not final and will be updated for re-runs.

## Test 1 : Pub-Sub 
This test is designed to primarily validate the hydra architecture while testing python zmq performance at scale.
The pattern is from one publisher to many subscribers. We are checking the packet rate performance as the number of 
subscribers change.
ZMQ explains the drop behaviour on pub sub here [LINK](http://zguide.zeromq.org/php:chapter5). 
Drop's are expected for scale, the test bed here is just characterising the drop behaviour for 
some basic deployment scenarios. 
Its fairly easy to modify the test cases to reflect different deployments and test for them.

Also note that the drop's completely disappear if we she the send watermark to 0 on the publisher.

```
    int hwm = 0;
    socket_pub.setsockopt(ZMQ_SNDHWM, &hwm, sizeof(hwm));
```

This will cause memory to grow and/or the performance to be affected if clients are slow. i.e. the performance will drop 
down towards the slowest of the clients. (Would be good to have some testcase for this as well)

For CPP ZMQ_SNDHWM is set to 1000 by default. 

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

### Results (ZMQ - PYTHON Pub/Sub)
Table showing results on client count and message rate (Packets Per Second). Likely the packets are minimum size.

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=1193589650&format=image">

At 10k clients the python publisher was having problem responding to commands and calls where timing out, so there is 
no data gathered at that sample. (Will debug this, likely need to add one more mesos worker to get to 10k) 

The last column on the table shows this number under "Publisher Packet Rate", varies around 2.5Mpps. 
The publisher packet rate is almost linear for all the samples. 
The cpu usages during these experiments always peeked with PUB using ~200%. 
The publisher node had a network bandwidth usage of around 50~70MBps for the duration of the tests.
  
 Keep in mind ZMQ does not guarantee delivery in pub-sub model and packet drops are expected. Here we are just 
 characterising the drop behaviour. Also setting the SNDHWM (send water mark) on the PUB socket to 0 (infinity) will 
 get rid of all the drops at the risk of a slow client causing huge increase in memory and drop in performance. 
 Increasing the value from default of 1k will be a good choice for most applications.

For this the command line is
`>hydra zmqrate`

### Results (ZMQ - CPP Pub/Sub)

For the CPP test the results where very similar to python test. With CPP the rates are all generally higher then python.
Also the publisher is able to push lot more traffic so we are seeing a much higher drop rate especially at low load. 

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=682891645&format=image">

I did not modify the HWM threshold value, as it will depend a lot on the application. However I am sure I can find a 
high enough number that will reduce the drop rate to negligible. 


## Introducing slow Clients 

## Notes

Since the pub sub is designed such that the pub has no feedback, it's not seem easy to generate the traffic such that 
majority of the subscriber's receive the message without drop. 
In the experiments it was fairly easy to create huge amount of drops with small number of clients.

If I was to design a publisher that slows down such that it can match the rate of the majority of the subscribers and 
 only drop packets towards the really slow subscribers. ( Will see if this is possible ?)





To Plot 
> The maximum sub rate that can be achieved with no drops w.r.t client count
> The maximum sub rate with < 1% drop 
> Effect on maximum sub rate with few of the clients being slow 
> Effect on maximum sub rate with few of the clients connecting and disconnecting. 
