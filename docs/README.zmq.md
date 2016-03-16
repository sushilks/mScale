# ZMQ Client scale testing.

The initial setup is up an running, now it's possible to spawn thousands of clients. 
## Test 1 : Pub-Sub 
This test is designed to primarily validate the hydra architecture while testing python zmq performance at scale.
The performance of one publisher to many subscriber is being checked here. 

### Test setup 
This involved 4 servers on google cloud
One server was dedicated to running zmq-pub
the other three where dedicated for running zmq-sub

### Command line 
`>hydra zmqsuit`

### Test methodology 
The test orchestrates the launch of publisher and the subscriber jobs on mesos cluster, (they are executed
as processes on the nodes. Not using any containers)
Once the process are up and running the test triggers the publisher to send different rate of traffic for 60 seconds. 
After the time interval rates are measured across all the subscribers and averaged. 
We keep increasing the rate till the publisher can not see any more increase and log it as the max rate. 

### Results
Table showing results on client count and message rate

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=1193589650&format=image">


Here is a graph showing the maximum rate of message received at the subscribers as a function of number of clients.

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=971303165&format=image">

This chart is showing packet drops with increase in the number of clients.

<img src="https://docs.google.com/spreadsheets/d/1BFmQ1xvnga44r15BGnTzCUcs5i-dleNMZ1bsnh8j2rg/pubchart?oid=632762905&format=image">

At 10k clients the python publisher was having problem responding to commands and calls where timing out, so there is 
no data gathered at that sample. 

It's interesting to note that the packet drop rate spikes up at around 80 clients and then drops down.



test


## Notes
Add additional test cases to measure here
