#!/bin/bash
# 
# proto/gRPC paths from protoc are a nightmare in python. Fix up the 
# install location and associated import paths/symbol names because
# the provided package is out of date with latest protobuf and is 
# unusable. 
# 
ROOT_DIR=generated/python/standardproto
mkdir -p ${ROOT_DIR}/grpc_health_check
cp -r ${ROOT_DIR}/src/proto/grpc/health/* ${ROOT_DIR}/grpc_health_check
for F in $( find ${ROOT_DIR}/grpc_health_check -type f ) ; do
    sed -Ei.bak 's/src\.proto\.grpc\.health\./grpc_health_check\./g' $F
    # sed -Ei.bak 's/src\/proto\/grpc\/health\//grpc_health_check\//g' $F
    sed -Ei.bak 's/src_dot_proto_dot_grpc_dot_health_dot/grpc_health_check_dot/g' $F
    rm $F.bak
done
rm -rf ${ROOT_DIR}/src
