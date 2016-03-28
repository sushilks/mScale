PROTO_DIR=../../python/hydra/lib
PROTO_FILE=hdaemon.proto
CPP_OPT=-std=c++0x -g
DEST_DIR=../../scripts

all: ${DEST_DIR}/zmq_pub ${DEST_DIR}/zmq_sub

${DEST_DIR}/zmq_pub: zmq_pub.cc hdaemon.pb.cc
	g++ ${CPP_OPT} -I. hdaemon.pb.cc zmq_pub.cc -lzmq -lprotobuf -o ${DEST_DIR}/zmq_pub

${DEST_DIR}/zmq_sub: zmq_sub.cc hdaemon.pb.cc
	g++ ${CPP_OPT} -I. hdaemon.pb.cc zmq_sub.cc -lzmq -lprotobuf -o ${DEST_DIR}/zmq_sub

hdaemon.pb.cc: ${PROTO_DIR}/${PROTO_FILE}
	protoc --cpp_out=. --proto_path ${PROTO_DIR} ${PROTO_DIR}/${PROTO_FILE}

clean:
	rm zmq_pub
