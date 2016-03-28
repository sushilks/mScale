CWD=`pwd`
cd $CWD/src/main/python/hydra/lib && protoc --python_out=. ./hdaemon.proto
#cd $CWD/src/main/c/zmq && make && mv ./zmq_pub ../../../../live
cd $CWD/src/main/c/zmq && make
cd $CWD
