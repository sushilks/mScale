# KAFKA Client Scale Test

### Kafka Tests

In general terms, the goal of this test is to stress the distributed messaging system **Apache Kafka** with increased load. Our use case involves one *kafka-pub* sending records (likely small messages) at a defined (maximum) transmission rate to the Kafka Server (i.e., cluster, herein comprising a single broker) which holds on to these records and hands them out to consumer(s).

The results shown in this document can be reproduced on any cloud or physical setup. In addition we have included an IPython Notebook under `src/main/python/hydra/kafkatest/jupyter/` which eases the generation of tables and graphs for the same scenarios that we have tested.

**IMPORTANT**

   These tests where initially run using the **kafka-python** client (available at: https://github.com/dpkp/kafka-python), however, producer's throughput was significantly under expected rate (when compared against benchmark reported values and those obtained by running the integrated kafka performance tool). For this reason, we alternatively used the **pykafka** client (available at: https://github.com/Parsely/pykafka) which clearly outperformed the former library.

**DISCLAIMER**
   This is still WORK IN PROGRESS and will be progressively updated.  

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
    * Consumer Buffer Max Size
- Maximum publisher rate without any drops as the number of client's increases.  

#### **Results Test 1:** *Producer Throughput as a function of batch size*

The Kafka producer is running in an *asynchronous mode* which is essentially an important setting to get the best performance in terms of throughput. When in this mode, the producer keeps an in-memory queue of messages which are then sent in batches to the broker. The batch size in [bytes] is a parameter that can be defined by the user.

The results show how the producer's throughput changes as a function of the batch size. Essentially throughput is shown to improve--to a certain extent--with an increase of the batch size. There is a clear trade-off between latency and throughput, i.e., rather then sending one message at a time we are delaying messages to be sent in batches, which turns down latency but increases throughput.

Next, we present performance results in a Table and the following graphs depict the **average producer rate [pps]**, **average client rate [pps]** and **average packet loss [%]** as a function of the **batch size**.


**KAFKA-PYTHON CLIENT RESULTS**

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


**PYKAFKA CLIENT RESULTS**

|   Client # |   Batch |   Avrg Tx Rate |   Avrg Rx Rate |   Client Loss[%] |   Failed Clients | Total pckts Tx   | Total pckts Rx   |
|-----------:|--------:|---------------:|---------------:|-----------------:|-----------------:|:-----------------|:-----------------|
|        960 |     200 |        20646   |        475.379 |         18.0642  |              305 | 206470           | 169172           |
|        960 |     500 |        21680.2 |        473.972 |         18.8726  |              303 | 216803           | 175886           |
|        960 |    1000 |        21482.4 |        467.672 |         20.2038  |              455 | 214825           | 171422           |
|        960 |    2000 |        18722.2 |        494.646 |         15.9007  |              246 | 187222           | 157452           |
|        960 |    5000 |        19872.7 |        471.189 |         17.0968  |              284 | 198728           | 164751           |
|         30 |     200 |        23613   |      10154.6   |          1.32814 |                3 | 236267           | 233129           |
|         30 |     500 |        23515.7 |       6427.79  |         18.645   |               17 | 235202           | 191348           |
|         30 |    1000 |        24901.2 |      10231.5   |          4.82651 |                5 | 249013           | 236994           |
|         30 |    2000 |        24352.2 |       9894.25  |          4.18307 |                6 | 243523           | 233336           |
|         30 |    5000 |        23842.7 |       9540.05  |          5.69791 |                7 | 238427           | 224841           |
|         60 |     200 |        23914.2 |       2915.44  |         16.9635  |               25 | 239143           | 198576           |
|         60 |     500 |        21630.8 |       9452.7   |          1.81988 |                5 | 216308           | 212371           |
|         60 |    1000 |        21954.3 |       8197.49  |          7.05474 |               14 | 219543           | 204054           |
|         60 |    2000 |        22220.1 |       8375.48  |          4.49105 |               10 | 222201           | 212221           |
|         60 |    5000 |        20545.2 |       9553.08  |          3.96436 |                9 | 205452           | 197307           |
|        120 |     200 |        19576.2 |       4770.66  |          5.01561 |               21 | 195762           | 185943           |
|        120 |     500 |        19651   |       4829.79  |          5.03766 |               21 | 196510           | 186610           |
|        120 |    1000 |        20605.3 |       4799.83  |          4.55567 |               19 | 206231           | 196835           |
|        120 |    2000 |        19884.9 |       4798.92  |          5.17319 |               26 | 198851           | 188564           |
|        120 |    5000 |        20477.6 |       4779.5   |          7.35196 |               21 | 204809           | 189751           |
|        480 |     200 |        19931.1 |       1073.62  |         10.2422  |               83 | 199311           | 178897           |
|        480 |     500 |        15326.8 |       1092.26  |          2.72844 |               29 | 153289           | 149106           |
|        480 |    1000 |        15606.3 |       1041.91  |         14.1434  |              154 | 156063           | 133990           |
|        480 |    2000 |        18351.1 |       1049.26  |          9.71524 |               80 | 183511           | 165682           |
|        480 |    5000 |        21661.5 |       1076.5   |          6.02582 |               54 | 216624           | 203570           |
|        240 |     200 |        22814.7 |       2033.41  |          5.18104 |               30 | 228339           | 216508           |
|        240 |     500 |        20140.6 |       2137.01  |          7.08103 |               33 | 201409           | 187147           |
|        240 |    1000 |        20414.5 |       2218.47  |         21.134   |               77 | 204174           | 161023           |
|        240 |    2000 |        20375.3 |       2095.42  |          4.92151 |               29 | 203759           | 193730           |
|        240 |    5000 |        20340.1 |       2095.18  |          5.78136 |               39 | 203402           | 191642           |


<div>
    <a href="https://plot.ly/~anny.martinez/42/" target="_blank" title="Average Producer Rate vs. Batch" style="display: block; text-align: center;"><img src="https://plot.ly/~anny.martinez/42.png" alt="Average Producer Rate vs. Batch" style="max-width: 100%;width: 1129px;"  width="1129" onerror="this.onerror=null;this.src='https://plot.ly/404.png';" /></a>
    <script data-plotly="anny.martinez:42"  src="https://plot.ly/embed.js" async></script>
</div>

<div>
    <a href="https://plot.ly/~anny.martinez/43/" target="_blank" title="Average Client Rate vs. Batch" style="display: block; text-align: center;"><img src="https://plot.ly/~anny.martinez/43.png" alt="Average Client Rate vs. Batch" style="max-width: 100%;width: 1129px;"  width="1129" onerror="this.onerror=null;this.src='https://plot.ly/404.png';" /></a>
    <script data-plotly="anny.martinez:43"  src="https://plot.ly/embed.js" async></script>
</div>

<div>
    <a href="https://plot.ly/~anny.martinez/44/" target="_blank" title="Average Packet Loss vs. Batch" style="display: block; text-align: center;"><img src="https://plot.ly/~anny.martinez/44.png" alt="Average Packet Loss vs. Batch" style="max-width: 100%;width: 1129px;"  width="1129" onerror="this.onerror=null;this.src='https://plot.ly/404.png';" /></a>
    <script data-plotly="anny.martinez:44"  src="https://plot.ly/embed.js" async></script>
</div>



**Command Line**

   This test can be run directly on IPython Notebook: `kafkatest/jupyter/kafka` and export your report along with tables and graphics or using the following command:

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
