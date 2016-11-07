FROM sdp-docker-registry.kat.ac.za:5000/docker-base

MAINTAINER Bruce Merry "bmerry@ska.ac.za"

USER root

RUN apt-get -y update && apt-get install --no-install-recommends -y \
        opencl-headers

RUN VERSION=367.57 && \
    DRIVER_RUN_FILE=NVIDIA-Linux-x86_64-$VERSION.run && \
    wget --progress=dot:mega "http://sdp-services.kat.ac.za/mirror/uk.download.nvidia.com/XFree86/Linux-x86_64/$VERSION/$DRIVER_RUN_FILE" && \
    sh ./$DRIVER_RUN_FILE --no-kernel-module --silent --no-network && \
    rm -- $DRIVER_RUN_FILE

RUN CUDA_RUN_FILE=cuda_7.5.18_linux.run && \
    wget --progress=dot:mega "http://sdp-services.kat.ac.za/mirror/developer.download.nvidia.com/compute/cuda/7.5/Prod/local_installers/$CUDA_RUN_FILE" && \
    sh ./$CUDA_RUN_FILE -silent -toolkit && \
    rm -- $CUDA_RUN_FILE

ENV PATH="$PATH:/usr/local/cuda/bin"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64"

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
