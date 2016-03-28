

#include <zmq.hpp>
#include <stdio.h>
#include <unistd.h>
#include <string>
#include <assert.h>
#include <stdlib.h>
#include <ctime>
#include "hdaemon.pb.h"

#include <iostream>
class TestControl {
 public:
  TestControl() {
    publishing = start_publishing = false;
    test_duration = 5;
    msg_batch = 100;
    msg_requested_rate = 1000;
    msg_cnt = 0;
  }
  uint64_t start_test() {
    floatStats.clear();
    intStats.clear();
    uint64_t start_time = std::time(0);
    intStats["time:start"] = start_time;
    msg_cnt = 0;
    return start_time;
  }
  void stop_test() {
    // do stats calculation here
    intStats["time:end"] = std::time(0);
    uint64_t elapsed_time = intStats["time:end"] - intStats["time:start"];
    floatStats["rate"] = 1.0 * msg_cnt / elapsed_time;
    intStats["count"] = msg_cnt;
  }
  bool publishing;
  bool start_publishing;
  std::map <std::string, uint64_t> intStats;
  std::map <std::string, float> floatStats;
  uint32_t test_duration;
  uint32_t msg_batch;
  uint32_t msg_requested_rate;
  uint64_t msg_cnt;
};

void process_message(const std::string& msg, TestControl* tctrl, std::string* resp) {
  hydra::CommandMessage cmsg;
  hydra::ResponseMessage rmsg;
  hydra::ResponseMessage_Resp* r;
  if (!cmsg.ParseFromString(msg)) {
    rmsg.set_status("error");
    r = rmsg.add_resp();
    r->set_name("__r");
    r->set_strvalue("Unable to parse the protobuf string!!!");
    printf("Unable to parse protbuf message received of size %d\n", (int)msg.size());
  } else if (cmsg.type() == hydra::CommandMessage::SUBCMD && cmsg.has_cmd()) {
    std::string cmd_name = cmsg.cmd().cmd_name();
    printf("Received a command [%s]\n", cmd_name.c_str());
    fflush(NULL);
    if (cmd_name == "ping") {
      // PING - PONG.
      rmsg.set_status("ok");
      r = rmsg.add_resp();
      r->set_name("__r");
      r->set_strvalue("pong");
    } else if (cmd_name == "start") {
      // START of test.
      r = rmsg.add_resp();
      r->set_name("__r");
      if (tctrl->publishing  || tctrl->start_publishing) {
        rmsg.set_status("error");
        r->set_strvalue("test is still running, cant start.");
      } else {
        rmsg.set_status("ok");
        r->set_strvalue("starting");
        tctrl->start_publishing = true;
      }
    } else if (cmd_name == "teststatus") {
      // get test status
      rmsg.set_status("ok");
      std::string tstatus;
      if (tctrl->publishing && tctrl->start_publishing)
        tstatus = "running";
      else if (tctrl->publishing && !tctrl->start_publishing)
        tstatus = "stopping";
      else if (!tctrl->publishing && tctrl->start_publishing)
        tstatus = "starting";
      else
        tstatus = "stopped";
      r = rmsg.add_resp();
      r->set_name("__r");
      r->set_strvalue(tstatus);
      printf("\t -> TestStatus:%s\n", tstatus.c_str());
    } else if (cmd_name == "updatepub") {
      // update test properties
      for (int i = 0; i < cmsg.cmd().argument_size(); ++i) {
        hydra::CommandMessage_CommandArgs arg = cmsg.cmd().argument(i);
        printf("\t -> name = %s [int:%d float:%d str:%d]\n", arg.name().c_str(), arg.has_intvalue(), arg.has_floatvalue(), arg.has_strvalue());
        fflush(NULL);
        if (arg.name() == "test_duration") {
          assert(arg.has_intvalue());
          tctrl->test_duration = arg.intvalue();
          printf("\t    -> updatedpub test_duration=%d\n", tctrl->test_duration);
        } else if (arg.name() == "msg_batch") {
          assert(arg.has_intvalue());
          tctrl->msg_batch = arg.intvalue();
          printf("\t    -> updatedpub msg_batch=%d\n", tctrl->msg_batch);
        } else if (arg.name() == "msg_requested_rate") {
          assert(arg.has_intvalue() || arg.has_floatvalue());
          if (arg.has_intvalue())
            tctrl->msg_requested_rate = arg.intvalue();
          else
            tctrl->msg_requested_rate = arg.floatvalue();
          printf("\t    -> updatedpub msg_requested_rate=%d\n", tctrl->msg_requested_rate);
        }
      }
      rmsg.set_status("ok");
    } else if (cmd_name == "stats") {
      rmsg.set_status("ok");
      for (auto it = tctrl->intStats.begin();
           it != tctrl->intStats.end();
           ++it) {
        r = rmsg.add_resp();
        r->set_name(it->first);
        r->set_intvalue(it->second);
      }
      for (auto it = tctrl->floatStats.begin();
           it != tctrl->floatStats.end();
           ++it) {
        r = rmsg.add_resp();
        r->set_name(it->first);
        r->set_floatvalue(it->second);
      }
    } else {
      // INVALID COMMAND.
      rmsg.set_status("error");
      r = rmsg.add_resp();
      r->set_name("__r");
      std::string m = "Did not find implemented for Command ";
      m += cmd_name;
      r->set_strvalue(m);
    }
  } else {
    rmsg.set_status("error");
    r = rmsg.add_resp();
    r->set_name("__r");
    std::string m = "Did not find Command in the message or cmd type[" + std::to_string(cmsg.type()) + "] is incorrect";
    r->set_strvalue(m);
  }
  printf("    -> Responding with status [%s]\n", rmsg.status().c_str());
  fflush(NULL);
  assert(rmsg.SerializeToString(resp));
}
  // ping
  // start
  // get stats
  // test status
  // update pub metrics

  // parse protobuf
  // extract command
  // process command
  // create response
  // send reply


int main (void) {
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  zmq::context_t context(1);
  zmq::socket_t socket_rep(context, ZMQ_REP);
  zmq::socket_t socket_pub(context, ZMQ_PUB);

  int hwm = 0;
  socket_pub.setsockopt(ZMQ_SNDHWM, &hwm, sizeof(hwm));
  //int sbuf = 1024 * 16;
  //  socket_sub.setsockopt(ZMQ_SNDBUF, &sbuf, sizeof(sbuf));

  std::string strPort = std::string(getenv("PORT0"));
  printf("Starting Rep Server on port %s\n", strPort.c_str());
  fflush(NULL);
  socket_rep.bind("tcp://*:" + strPort);
  socket_pub.bind("tcp://*:15556");

  TestControl tctrl;
  uint32_t cnt = 0;
  uint64_t start_time;
  char message_ch[120];
  while(true) {
    zmq_pollitem_t items[] = {
        {socket_rep, 0, ZMQ_POLLIN, 0}
    };
    int rc = zmq_poll(items, 1, 0);
    if (rc == -1) {
        printf("ZMQ POLL had error \n");
        break;
    }
    if (items[0].revents & ZMQ_POLLIN) {
        zmq::message_t request;
        socket_rep.recv(&request);
        std::string resp;
        process_message(std::string((char *)request.data(), request.size()),
                        &tctrl, &resp);
        zmq::message_t reply(resp.c_str(), resp.size());
        socket_rep.send(reply);
    }

    if (!tctrl.publishing && tctrl.start_publishing) {
        tctrl.publishing = true;
        start_time = tctrl.start_test();
        cnt = 0;
        printf("Starting the test\n"); fflush(NULL);
    } else if (tctrl.publishing && !tctrl.start_publishing) {
      tctrl.publishing = false;
      tctrl.stop_test();
      printf("Stopped the test\n"); fflush(NULL);
    } else if (!tctrl.publishing) {
      // to prevent spinning while test is idle
      sleep(1);
    }
    // Send the message to pub
    while (tctrl.publishing) {
       ++cnt;
      if (cnt >= (tctrl.msg_batch-1)) {
        // check cnt and delay if needed
        if (cnt == (tctrl.msg_batch - 1))
           break; // break once before sleep to allow poll to
          // use up some of the delay
          if (cnt >= tctrl.msg_batch) {
           time_t duration = std::time(0) - start_time;
           time_t exp_time = tctrl.msg_cnt / tctrl.msg_requested_rate;
           time_t delay = 0;

           if (duration > tctrl.test_duration) {
             tctrl.start_publishing = false;
             break;
           }
           if (exp_time > duration)
             delay = exp_time - duration;
           if (delay > 1) delay = 1;
           sleep(delay);
           cnt = 0;
         }
       }
       // send some data
       //std::strig str_msgcnt = atoi(msg_cnt);
       //std::string msg = str_msgcnt + " msg" + str_msgcnt;
       snprintf(message_ch, sizeof(message_ch),
        "%ld msg%ld",tctrl.msg_cnt, tctrl.msg_cnt);
       zmq::message_t message(strlen(message_ch));
       memcpy(message.data(), message_ch, strlen(message_ch));
       //message.rebuild(message_ch, strlen(message_ch));
       rc = socket_pub.send(message);
       if (!rc)
         printf(" ERROR Failed to send message %s\n", message_ch);
       ++tctrl.msg_cnt;
     } // while(publishing)
   } // while(true)
  return 0;
}
