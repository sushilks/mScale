

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
    msg_cnt = 0;
  }
  std::map <std::string, uint64_t> intStats;
  std::map <std::string, float> floatStats;
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
    } else if (cmd_name == "reset") {
      // update test properties
      tctrl->msg_cnt = 0;
      tctrl->intStats["first_msg_time"] = 0;
      tctrl->intStats["last_msg_time"] = 0;
      rmsg.set_status("ok");
    } else if (cmd_name == "stats") {
      rmsg.set_status("ok");
      //tctrl->intStats["last_msg_time"] = std::time(0);
      float duration = tctrl->intStats["last_msg_time"] - tctrl->intStats["first_msg_time"];
      tctrl->intStats["msg_cnt"] = tctrl->msg_cnt;
      tctrl->floatStats["rate"] = 1.0 * tctrl->msg_cnt / duration;
      for (auto it = tctrl->intStats.begin();
           it != tctrl->intStats.end();
           ++it) {
        r = rmsg.add_resp();
        r->set_name(it->first);
        r->set_intvalue(it->second);
        printf(" -> STATS : Reporting Back int [%s]=%ld\n",it->first.c_str(), it->second);
      }
      for (auto it = tctrl->floatStats.begin();
           it != tctrl->floatStats.end();
           ++it) {
        r = rmsg.add_resp();
        r->set_name(it->first);
        r->set_floatvalue(it->second);
        printf(" -> STATS : Reporting Back float [%s]=%f\n",it->first.c_str(), it->second);
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


int main (int argc, char** argv) {
  GOOGLE_PROTOBUF_VERIFY_VERSION;

  zmq::context_t context(1);
  zmq::socket_t socket_rep(context, ZMQ_REP);
  zmq::socket_t socket_sub(context, ZMQ_SUB);

  /*  int hwm = 0;
  socket_sub.setsockopt(ZMQ_RCVHWM, &hwm, sizeof(hwm));
  int rbuf = 1024 * 16;
  socket_sub.setsockopt(ZMQ_RCVBUF, &rbuf, sizeof(rbuf));
  */
  std::string strPort = std::string(getenv("PORT0"));


  if (argc != 3) {
    printf("Usages:: zmq_sub <pub_ip> <pub_port>\n");
    return 1;
  }
  std::string pub_ip(argv[1]);
  std::string pub_port(argv[2]);

  printf("Starting Rep Server on port %s\n", strPort.c_str());
  printf("Starting Sub to server at %s:%s\n", pub_ip.c_str(), pub_port.c_str());
  fflush(NULL);
  socket_rep.bind("tcp://*:" + strPort);
  socket_sub.connect("tcp://" + pub_ip + ":" + pub_port);
  socket_sub.setsockopt(ZMQ_SUBSCRIBE, "", 0);


  TestControl tctrl;
  uint32_t cnt = 0;
  uint64_t start_time;
  char message_ch[120];
  while(true) {
    zmq_pollitem_t items[] = {
      {socket_rep, 0, ZMQ_POLLIN, 0},
      {socket_sub, 0, ZMQ_POLLIN, 0}
    };
    int rc = zmq_poll(items, 2, -1);
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
    if (items[1].revents & ZMQ_POLLIN) {
      // SUB message
      zmq::message_t subm;
      socket_sub.recv(&subm);
      if(tctrl.msg_cnt == 0)
        tctrl.intStats["first_msg_time"] = std::time(0);
      tctrl.msg_cnt++;
      tctrl.intStats["last_msg_time"] = std::time(0);
    }
   } // while(true)
  return 0;
}
