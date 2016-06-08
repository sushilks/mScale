# KAFKA Client Scale Test

### Kafka Tests

In general terms, the goal of this test is to stress the distributed messaging system **Apache Kafka** with increased load. Our use case involves one *kafka-pub* sending records (likely small messages) at a defined (maximum) transmission rate to the Kafka Server (i.e., cluster, herein comprising a single broker) which holds on to these records and hands them out to consumer(s).

The results shown in this document can be reproduced on any cloud or physical setup. In addition we have included an IPython Notebook under `src/main/python/hydra/kafkatest/jupyter/` which eases the generation of tables and graphs for the same scenarios that we have tested.


### Test Setup

For these tests, we had a total of five (5) google cloud instances, with the following specs:

* 1 server (n1-standard-4) dedicated to marathon/mesos-master/zookeeper and hosting **hydra**.
* 1 server (n1-standard-4) dedicated to run kafka-pub (producer app) & the kafka server (broker)
    - *Note*: The current scaling test deploys ONE broker, ONE topic and ONE partition.
* 3 servers (n1-standard-16) dedicated to run kafka-sub (consumers app)
    - *Note*: Each mesos-slave was configured with an 'attribute' as a means to 'tag' each node. The tags in use are:
        - **cpu4:mem16**: to tag (n1-standard-4) slave
        - **cpu4:mem16**: to tag (n1-standard-16) slaves

  For details on how to set attributes for a mesos-slave refer to the readme in /lake-lerna/hydra:
    https://open.mesosphere.com/reference/mesos-slave/


Software Versions in use:

- OS: Ubuntu 14.04
- Kernel: 3.19.0-59-generic
- Python version : 2.7.5
- Apache Kafka 0.9
- Kafka-Python version: 1.2.1


### Performance Results

In this section, we present performance results for all the scenarios that have been tested. The main targets of assessment are:

- Evaluate Throughput as a function (effect) of:
    * Producer batch_size
    * Producer linger_ms
    * Consumer ...
- Maximum publisher rate without any drops as the number of client's increases.  

#### **Results Test 1:** *Producer Throughput as a function of batch size*

The Kafka producer is running in an *asynchronous mode* which is essentially an important setting to get the best performance in terms of throughput. When in this mode, the producer keeps an in-memory queue of messages which are then sent in batches to the broker. The batch size in [bytes] is a parameter that can be defined by the user.

The results show how the producer's throughput changes as a function of the batch size.

[TODO: Add explanation why batch changes throughput]

Next, we present performance results in a Table and the following graphs depict the **average producer rate [pps]**, **average client rate [pps]** and **average packet loss [%]** as a function of the **batch size**.


We can push about 50MB/sec to the system. However, this number changes with the batch size. The below graphs show the relation between these two quantities.

|   Client # |   Batch |   Avrg Tx Rate |   Avrg Rx Rate |   Client Loss[%] |   Failed Clients | Total pckts Tx   | Total pckts Rx   |
|-----------:|--------:|---------------:|---------------:|-----------------:|-----------------:|:-----------------|:-----------------|
|         30 |     100 |        5780.59 |       3486.29  |         0        |                0 | 57806            | 57806            |
|         30 |     200 |        6505.97 |       6524.21  |         0        |                0 | 65060            | 65060            |
|         30 |     500 |        6920.04 |       7075.12  |         0        |                0 | 69201            | 69201            |
|         30 |    1000 |        6997.29 |       7029.74  |         0        |                0 | 69973            | 69973            |
|         30 |    2000 |        7035.7  |       7063.27  |         0        |                0 | 70359            | 70359            |
|         30 |    5000 |        7180.59 |       7211.13  |         0        |                0 | 71806            | 71806            |
|         60 |     100 |        5402.98 |       3643.28  |         0        |                0 | 54030            | 54030            |
|         60 |     200 |        6263.35 |       6286.16  |         0        |                0 | 62634            | 62634            |
|         60 |     500 |        6694.33 |       6576.2   |         0        |                0 | 66944            | 66944            |
|         60 |    1000 |        7080.36 |       6792.99  |         0        |                0 | 70804            | 70804            |
|         60 |    2000 |        7037.93 |       6772.53  |         0        |                0 | 70380            | 70380            |
|         60 |    5000 |        7003.65 |       6722.81  |         0        |                0 | 70037            | 70037            |
|        120 |     100 |        5105.74 |       3505.87  |         0        |                0 | 51058            | 51058            |
|        120 |     200 |        6489.98 |       5000.97  |         0        |                0 | 64900            | 64900            |
|        120 |     500 |        7355.39 |       5130.57  |         0        |                0 | 73554            | 73554            |
|        120 |    1000 |        7162.48 |       5048.26  |         0        |                0 | 71625            | 71625            |
|        120 |    2000 |        7353.26 |       5027.6   |         0        |                0 | 73533            | 73533            |
|        120 |    5000 |        6100.36 |       4658.63  |         0        |                0 | 61004            | 61004            |
|        480 |     100 |        5899.89 |       1164.53  |         1.49009  |               15 | 58999            | 58119            |
|        480 |     200 |        6525.84 |       1134.03  |         0.348719 |                5 | 65259            | 65031            |
|        480 |     500 |        7231.53 |       1164.16  |         4.56227  |              212 | 72316            | 69016            |
|        480 |    1000 |        7140.09 |       1166.94  |         2.46217  |               23 | 71401            | 69642            |
|        480 |    2000 |        7228.85 |       1138.23  |         0.709657 |                8 | 72289            | 71775            |
|        480 |    5000 |        7163.34 |       1136.23  |         0.25466  |                4 | 71634            | 71451            |
|        240 |     100 |        5869.46 |       2415.06  |         0.295328 |                5 | 58696            | 58522            |
|        240 |     200 |        6599.42 |       2417.18  |         0.492246 |                4 | 65996            | 65671            |
|        240 |     500 |        7257.75 |       2385.41  |         0.642668 |                4 | 72579            | 72112            |
|        240 |    1000 |        7225.22 |       2356.39  |         0.120958 |                2 | 72253            | 72165            |
|        240 |    2000 |        7361.38 |       2410.17  |         0.935601 |                6 | 73614            | 72925            |
|        240 |    5000 |        7010.18 |       2374.95  |         0.431538 |                4 | 70102            | 69799            |

---

<div>
    <a href="https://plot.ly/~anny.martinez/30/" target="_blank" title="Average Producer Rate vs. Batch" style="display: block; text-align: center;"><img src="https://plot.ly/~anny.martinez/30.png" alt="Average Producer Rate vs. Batch" style="max-width: 100%;width: 1129px;"  width="1129" onerror="this.onerror=null;this.src='https://plot.ly/404.png';" /></a>
    <script data-plotly="anny.martinez:30"  src="https://plot.ly/embed.js" async></script>
</div>


<div>
    <a href="https://plot.ly/~anny.martinez/31/" target="_blank" title="Average Client Rate vs. Batch" style="display: block; text-align: center;"><img src="https://plot.ly/~anny.martinez/31.png" alt="Average Client Rate vs. Batch" style="max-width: 100%;width: 1129px;"  width="1129" onerror="this.onerror=null;this.src='https://plot.ly/404.png';" /></a>
    <script data-plotly="anny.martinez:31"  src="https://plot.ly/embed.js" async></script>
</div>


<div>
    <a href="https://plot.ly/~anny.martinez/32/" target="_blank" title="Average Packet Loss vs. Batch" style="display: block; text-align: center;"><img src="https://plot.ly/~anny.martinez/32.png" alt="Average Packet Loss vs. Batch" style="max-width: 100%;width: 1129px;"  width="1129" onerror="this.onerror=null;this.src='https://plot.ly/404.png';" /></a>
    <script data-plotly="anny.martinez:32"  src="https://plot.ly/embed.js" async></script>
</div>

---
**Command Line**

   This test can be run directly on IPython Notebook: `kafkatest/jupyter/Kafka Test` and export your report along with tables and graphics or using the following command:

        hydra kafka-batch

 #### **Results Test 2:** *Fixed Publisher Rate*

 The following test, sets the publisher rate to a fixed value (10000 [pps]) and assesses the performance of the system while the number of clients increases. In this test we have fixed the `msg_batch` to 1000 and `linger_ms` to 10 [ms].  

 The results show that client loss is experienced under this scenario when the number of clients increases beyond 120.


 |   Client # |   Avrg Tx Rate |   Avrg Rx Rate |   Client Loss[%] |   Failed Clients | Total pckts Tx   | Total pckts Rx   |
 |-----------:|---------------:|---------------:|-----------------:|-----------------:|:-----------------|:-----------------|
 |         30 |        7190.53 |       7225.42  |         0        |                0 | 71906            | 71906            |
 |         60 |        6999.73 |       6860.66  |         0        |                0 | 69998            | 69998            |
 |        120 |        7602.66 |       1569.84  |         2.45713  |                8 | 76027            | 74158            |
 |        240 |        7455.71 |       2453.13  |         0.494229 |                6 | 74558            | 74189            |
 |        480 |        7449.06 |       1173.02  |         1.4111   |               15 | 74491            | 73439            |
 |        960 |        7313.26 |        575.527 |         0.739413 |               18 | 73133            | 72592            |
 |       1920 |        6446.53 |        281.702 |         1.4252   |               48 | 64466            | 63547            |



#### Maximum publisher rate without any drops as the number of client's increases





















---

# COPY/PASTE EDIT BEFORE OR USE AS TEMPLATE

# ZMQ Client scale testing.



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

|Client Count|MaxRate at SUB With Drop|Aggregate Max pps|MaxRate at Sub (< 0.5% Drop, SNDHWN=1k)|MaxRate at Sub(SNDHWM = 100k)|MaxRate at Sub(SNDHWM = 0)|
| --- | --- | --- | --- | ---| ---|
|30     |207652	|6,229,560	|3251	|40207 |217985
|60	    |109096	|6,545,760	|2906	|23360 |111175
|120	|54594	|6,551,280	|4492	|17087 |54984
|240	|18406	|4,417,440	|4249	|11142 |27778
|480	|8756	|4,202,880	|4317	|8756  |8622
|960	|3658	|3,511,680	|3658	|3658  |3404
|1920	|1976	|3,793,920	|1976	|1976  |1975
|3840	|1239	|4,757,760	|1239	|1239  |1063
|7680	|538	|4,131,840	|538	|538   |520

Three samples where collected for maximum achievable rate with < 0.5% drop

   * with default SNDHWM of 1000.
   * with SNDHWM set to 100k for the publisher.
   * with SNDHWM set to 0. (Infinite queue size).

When the number of clients is low it's relatively easy to drop, and the rate needs to be very low(3251 compare
to max rate of 118k) to get no drop. Even increasing the SNDHWM form 1k to 100k we only see the max rate of 40k
only with infinite queue size we are able to get to the maximum rate possible.
Under low client load condition it seems very easy to drop packets.
This behaviour requires some more explanation, will work on digging a bit more to find why it's hard to get low drops
when the number of clients is very low.


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
