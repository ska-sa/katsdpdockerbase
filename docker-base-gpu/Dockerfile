FROM sdp-ingest5.kat.ac.za:5000/docker-base

MAINTAINER Bruce Merry "bmerry@ska.ac.za"

RUN VERSION=346.35 && \
    DRIVER_RUN_FILE=NVIDIA-Linux-x86_64-$VERSION.run && \
    MIRROR_HOST=mirror.kat.ac.za && \
    MIRROR_URL=http://192.168.1.25/nvidia && \
    wget "http://uk.download.nvidia.com/XFree86/Linux-x86_64/$VERSION/$DRIVER_RUN_FILE" && \
    #wget -q --header="Host: $MIRROR_HOST" "$MIRROR_URL/$DRIVER_RUN_FILE" && \
    sh ./$DRIVER_RUN_FILE --no-kernel-module --silent --no-network && \
    rm -- $DRIVER_RUN_FILE

RUN VERSION=6_5 && \
    CUDA_RUN_FILE=cuda_6.5.19_linux_64.run && \
    MIRROR_HOST=mirror.kat.ac.za && \
    MIRROR_URL=http://192.168.1.25/nvidia && \
    wget "http://developer.download.nvidia.com/compute/cuda/$VERSION/rel/installers/$CUDA_RUN_FILE" && \
    #wget "http://developer.download.nvidia.com/compute/cuda/$VERSION/Prod/local_installers/$CUDA_RUN_FILE" && \
    #wget -q --header="Host: $MIRROR_HOST" "$MIRROR_URL/$CUDA_RUN_FILE" && \
    sh ./$CUDA_RUN_FILE -silent -toolkit && \
    rm -- $CUDA_RUN_FILE
