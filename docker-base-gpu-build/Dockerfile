ARG KATSDPDOCKERBASE_REGISTRY=sdp-docker-registry.kat.ac.za:5000
ARG TAG=latest

FROM $KATSDPDOCKERBASE_REGISTRY/docker-base-build:$TAG
LABEL maintainer="sdpdev+katsdpdockerbase@ska.ac.za"

USER root

# The CUDA installer has some requirements:
RUN apt-get -y update && apt-get install --no-install-recommends -y \
        opencl-headers ocl-icd-libopencl1 ocl-icd-opencl-dev

ARG KATSDPDOCKERBASE_MIRROR=http://sdp-services.kat.ac.za/mirror

RUN CUDA_RUN_FILE=cuda_11.7.0_515.43.04_linux.run && \
    mirror_wget --progress=dot:mega "http://developer.download.nvidia.com/compute/cuda/11.7.0/local_installers/$CUDA_RUN_FILE" && \
    sh ./$CUDA_RUN_FILE --silent --toolkit && \
    rm -- $CUDA_RUN_FILE && \
    rm -r /usr/local/cuda/doc && \
    rm -r /usr/local/cuda/extras && \
    rm -r /usr/local/cuda/libnvvp && \
    rm -r /usr/local/cuda/nsight* && \
    rm -r /usr/local/cuda/Sanitizer && \
    rm -r /usr/local/cuda/tools

ENV PATH="$PATH:/usr/local/cuda/bin" \
    PATH_PYTHON3="$PATH_PYTHON3:/usr/local/cuda/bin" \
    LIBRARY_PATH="/usr/local/cuda/lib64"
# Calling the file z_cuda puts it behind the system libraries in search
# order, which ensures that the system version of libOpenCL.so.1 (which is
# newer) is found in preference to the one provided with CUDA).
RUN echo '/usr/local/cuda/lib64' > /etc/ld.so.conf.d/z_cuda.conf && ldconfig

# Create information for locating the NVIDIA driver components. This isn't handled
# by nvidia-docker.
RUN mkdir -p /etc/OpenCL/vendors && \
    echo libnvidia-opencl.so.1 > /etc/OpenCL/vendors/nvidia.icd

USER kat

# Create wheels for GPU-related packages.
# numpy is installed first because pycuda doesn't use PEP 518 and so if numpy
# isn't installed before pycuda, setuptools will suck in the latest version
# while building it and the resulting wheel will break when used with older
# versions of numpy (specifically, older C_API_VERSION).
COPY requirements.txt /home/kat/docker-base/gpu-requirements.txt
RUN virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt && \
    install_pinned.py -c ~/docker-base/base-requirements.txt numpy && \
    install_pinned.py -c ~/docker-base/base-requirements.txt -r ~/docker-base/gpu-requirements.txt && \
    rm -rf ~/tmp-ve3

# For nvidia-container-runtime 
# driver backwards compatability not guaranteed across minor versions when using PTX:
# https://docs.nvidia.com/deploy/cuda-compatibility/index.html#application-considerations
ENV NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility NVIDIA_REQUIRE_CUDA=cuda>=11.7 

