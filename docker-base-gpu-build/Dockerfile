ARG KATSDPDOCKERBASE_REGISTRY=sdp-docker-registry.kat.ac.za:5000
ARG TAG=latest

FROM $KATSDPDOCKERBASE_REGISTRY/docker-base-build:$TAG
MAINTAINER Bruce Merry "bmerry@ska.ac.za"

USER root

# The CUDA installer has some requirements:
RUN apt-get -y update && apt-get install --no-install-recommends -y \
        opencl-headers ocl-icd-libopencl1 ocl-icd-opencl-dev

ARG KATSDPDOCKERBASE_MIRROR=http://sdp-services.kat.ac.za/mirror

RUN CUDA_RUN_FILE=cuda_10.0.130_410.48_linux && \
    mirror_wget --progress=dot:mega "https://developer.nvidia.com/compute/cuda/10.0/Prod/local_installers/$CUDA_RUN_FILE" && \
    sh ./$CUDA_RUN_FILE --silent --toolkit && \
    rm -- $CUDA_RUN_FILE /tmp/cuda* && \
    rm -r /usr/local/cuda/doc && \
    rm -r /usr/local/cuda/samples && \
    rm -r /usr/local/cuda/tools && \
    rm -r /usr/local/cuda/extras && \
    rm -r /usr/local/cuda/jre && \
    rm -r /usr/local/cuda/libnsight && \
    rm -r /usr/local/cuda/libnvvp

ENV PATH="$PATH:/usr/local/cuda/bin" \
    PATH_PYTHON2="$PATH_PYTHON2:/usr/local/cuda/bin" \
    PATH_PYTHON3="$PATH_PYTHON3:/usr/local/cuda/bin"
# /usr/lib/x86_64-linux-gnu is explicitly added to the front to prevent the
# CUDA version of libOpenCL.so.1 (which is older) from overriding the version
# installed by ocl-icd-opencl-dev.
ENV LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64"
ENV LIBRARY_PATH="/usr/local/cuda/lib64"

# Create information for locating the NVIDIA driver components. This isn't handled
# by nvidia-docker.
RUN mkdir -p /etc/OpenCL/vendors && \
    echo libnvidia-opencl.so.1 > /etc/OpenCL/vendors/nvidia.icd

USER kat

# Create wheels for GPU-related packages
COPY requirements.txt /home/kat/docker-base/gpu-requirements.txt
RUN virtualenv ~/tmp-ve && \
    . ~/tmp-ve/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -d ~/docker-base/base-requirements.txt -r ~/docker-base/gpu-requirements.txt && \
    rm -rf ~/tmp-ve
# Same for Python3
RUN virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -d ~/docker-base/base-requirements.txt -r ~/docker-base/gpu-requirements.txt && \
    rm -rf ~/tmp-ve3

# For nvidia-docker 1.0
LABEL com.nvidia.volumes.needed="nvidia_driver" com.nvidia.cuda.version="10.0"
# For nvidia-container-runtime
ENV NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility NVIDIA_REQUIRE_CUDA=cuda>=10.0
