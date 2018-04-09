FROM sdp-docker-registry.kat.ac.za:5000/docker-base

MAINTAINER Bruce Merry "bmerry@ska.ac.za"

USER root

RUN apt-get -y update && apt-get install --no-install-recommends -y \
        opencl-headers ocl-icd-libopencl1 ocl-icd-opencl-dev module-init-tools

RUN CUDA_RUN_FILE=cuda_8.0.44_linux-run && \
    wget --progress=dot:mega "http://sdp-services.kat.ac.za/mirror/developer.nvidia.com/compute/cuda/8.0/prod/local_installers/$CUDA_RUN_FILE" && \
    sh ./$CUDA_RUN_FILE --silent --toolkit && \
    rm -- $CUDA_RUN_FILE

ENV PATH="$PATH:/usr/local/nvidia/bin:/usr/local/cuda/bin"
ENV PATH_PYTHON3="$PATH_PYTHON3:/usr/local/nvidia/bin:/usr/local/cuda/bin"
# /usr/lib/x86_64-linux-gnu is explicitly added to the front to prevent the
# NVIDIA driver version of libOpenCL.so.1 (which is outdated) from overriding
# the version installed by ocl-icd-opencl-dev.
ENV LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/local/nvidia/lib:/usr/local/nvidia/lib64:/usr/local/cuda/lib64"

# Create information for locating the NVIDIA driver components. This isn't handled
# by nvidia-docker.
RUN mkdir -p /etc/OpenCL/vendors && \
    echo libnvidia-opencl.so.1 > /etc/OpenCL/vendors/nvidia.icd

USER kat

# Create wheels for GPU-related packages. First we need to disable the
# already-configured virtualenv, then create a new temporary one. Note that we
# don't need to reactivate the old one, because the environment only lasts to
# the end of the RUN step.
COPY requirements.txt /home/kat/docker-base/gpu-requirements.txt
RUN PATH="`echo $PATH | sed -e 's!/home/kat/ve/bin:!!'`" && \
    virtualenv ~/tmp-ve && \
    . ~/tmp-ve/bin/activate && \
    pip install --no-deps -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -d ~/docker-base/base-requirements.txt -r ~/docker-base/gpu-requirements.txt && \
    rm -rf ~/tmp-ve
# Same for Python3
RUN PATH="`echo $PATH | sed -e 's!/home/kat/ve/bin:!!'`" && \
    virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    pip install --no-deps -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -d ~/docker-base/base-requirements.txt -r ~/docker-base/gpu-requirements.txt && \
    rm -rf ~/tmp-ve3

# For nvidia-docker 1.0
LABEL com.nvidia.volumes.needed="nvidia_driver" com.nvidia.cuda.version="8.0"
# For nvidia-container-runtime
ENV NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility NVIDIA_REQUIRE_CUDA=cuda>=8.0
