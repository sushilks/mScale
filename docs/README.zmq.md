# ZMQ Client scale testing.

The initial setup is up an running, now it's possible to spawn thousands of clients. 
The test bed is written in a way that all the results here can be re-produced easily on any cloud or physical setup. 
For all our testing we are using google compute cloud.

We are still fixing bugs in the infra so the results are not final and will be updated for re-runs.

## Test 1 : Pub-Sub 
This test is designed to primarily validate the hydra architecture while testing zmq performance at scale.
The pattern is from one publisher to many subscribers.The things that we are trying to measure are 

* Maximum publisher rate without any drops as the number of client's increases
* Effect of a small percentage of slow subscribers on the overall system
* Effect of a small percentage of subscribers connecting/disconnecting to the publishers.

ZMQ explains the drop behaviour on pub sub here [LINK](http://zguide.zeromq.org/php:chapter5). 
Its fairly easy to modify the test cases to reflect different deployments and test for them.

Also note that the drop's completely disappear if we she the send watermark to 0 on the publisher.

```
    int hwm = 0;
    socket_pub.setsockopt(ZMQ_SNDHWM, &hwm, sizeof(hwm));
```

This will cause memory to grow and/or the performance to be affected if clients are slow. i.e. the performance will drop 
down towards the slowest of the clients. (Would be good to have some testcase for this as well)

The default value for ZMQ_SNDHWM is set to 1000, this is the send queue threshold on the publisher.  

### Test setup 
This involved 5 servers on google cloud

* 1 server (n1-standard-4) was dedicated to marathon-master/zookeeper etc.
* 1 server (n1-standard-4) was dedicated to running zmq-pub
* 3 servers(n1-standard-16) where dedicated for running zmq-sub

Versions of different software used.

* OS: Ubuntu 14.04
* Kernel: 3.19.0-51-generic
* Python version : 2.7.5
* Zmq Version : 4.1.4


### Command line 

`>hydra zmqrate`

### Test methodology 
The test orchestrates the launch of publisher and the subscriber jobs on mesos cluster, (they are executed
as processes on the nodes. Containers are not used to reduce the memory footprint for each client)
Once the process are up and running the test triggers the publisher to send different rate of traffic for 60 seconds. 
After the time interval rates are measured across all the subscribers and averaged. 
To identify max rate, the rate is increased till there is no observable increase on the received rate on the subscribe.
The maximum rate is also measured while a small percentage ~1% of the subscribers are running at 50% of the max rate 
observed in the first experiment.
one more mesurement of max rate is done while a small percentage ~1% of the subscribers are connecting/disconnecting
at the rate of 2 connections/second.

### Results (ZMQ - PYTHON Pub/Sub)
Table showing results on client count and message rate (Packets Per Second). Likely the packets are minimum size.

|Client Count|MaxRate at SUB With Drop|Aggregate Max pps|MaxRate at Sub (< 0.5% Drop)|10% of clients at Half Rate|10% of clients Reconnecting|
| --- | --- | --- | --- | ---| ---|
|30 |87286	|2,618,580	|77377	|73704	|74457|
|60	|46121	|2,767,260	|43607	|42811	|42319|
|120	|22645	|2,717,400	|21732	|21391	|22116|
|240	|11397	|2,735,280	|10758	|10725	|11125|
|480	|5669	|2,721,120	|5315	|5251	|5622|
|960	|2823	|2,710,080	|2665	|2575	|2814|
|1920	|1441	|2,766,720	|1368	|1399	|1444|
|3840	|735	|2,822,400	|712	|725	|763|
|7680	|368	|2,826,240	|368	|341	|396|


At 10k clients the python publisher was having problem responding to commands and calls where timing out, so there is 
no data gathered at that sample. (Will debug this, likely need to add one more mesos worker to get to 10k) 

"MaxRate at SUB with drop" shows the maximum packets rate that was received at the subscribers on a single client. 

The "Aggregate Max pps" column on the table shows this maximum amount of packets that the publisher is able to push 
it varies around 2.7Mpps. In most cases there are significant amount of drops at these rates, the drops reduces to zero 
as the scale approaches 7.6k clients. 

"MaxRate at Sub (<0.5% Drop)" indicates the maximum rate with minimal drops between pub-sub.

"10% of clients at half rate" indicates the effect of running 10% of the clients at slower rate (50% of max 
observed earlier).

"10% of the clients reconnecting" indicates the effect of 10% of the clients reconnecting at 10 connection/disconnection
every seconds.

The publisher packet rate is almost linear for all the samples as reflected by the "aggregate max pps".
The "Slow client" seem to reduce the performance by a very small amount for most cases.
The "Reconnecting client" shows better performance in general as when the clients are disconnected the load on the 
publisher is reduced. There is no major slowdown noticed due to socket connection/disconnection.

The cpu usages during these experiments always peeked with PUB using ~200%. 
The publisher node had a network bandwidth usage of around 50~70MBps for the duration of the tests.
  

For this the command line is
`>hydra zmqrate`


### Results (ZMQ - CPP Pub/Sub)

For the CPP test the results where very similar to python test. With CPP the rates are all generally higher then python.
Also the publisher is able to push lot more traffic so we are seeing a much higher drop rate even at low client load. 

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=682891645&format=image">

I did not modify the HWM threshold value, as it will depend a lot on the application. However I am sure I can find a 
high enough number that will reduce the drop rate to negligible. 



## Notes, Observations 

Since the zmq pub-sub is designed such that the pub has no feedback, it's not trivial to generate the traffic such that 
majority of the subscriber's receive the message without drop. 
In the experiments it was fairly easy to create huge amount of drops at small client loads, it became a bit 
more difficult at higher client load as majority of CPU was being used for sending packets.

What I would have like is to be able to publish at a rate such that majority of my subscribers get the data
without dropped many packets. In my experiments I can quickly get to 50% drop in packets at all clients which is very 
 undesirable, the publisher's job is to service as many subscribers as possible in this case it doing a poor job 
 serving every subscriber. 
Unfortunately zmq philosophy does not allow any information about the subscriber to 
propagate to the publisher so it's not possible to slow down the publisher to satisfy the majority. 
On the flip side, it forces the app developer to design the application to tolerate drops and scaling is fairly easy.
