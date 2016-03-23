CWD=`pwd`
cd $CWD/src/main/python/hydra/lib && protoc --python_out=. ./hdaemon.proto
#rm -f $CWD/src/main/c/zmq/hdaemon.proto
#ln -s $CWD/src/main/python/hydra/lib/hdaemon.proto $CWD/src/main/c/zmq/
#cd $CWD/src/main/c/zmq && make && mv ./zmq_pub ../../../../live
cd $CWD

