FROM sdp-docker-registry.kat.ac.za:5000/docker-base

MAINTAINER Bruce Merry "bmerry@ska.ac.za"

USER root

RUN apt-get -y update && apt-get install --no-install-recommends -y \
        opencl-headers ocl-icd-libopencl1 module-init-tools

RUN VERSION=367.57 && \
    DRIVER_RUN_FILE=NVIDIA-Linux-x86_64-$VERSION.run && \
    wget --progress=dot:mega "http://sdp-services.kat.ac.za/mirror/uk.download.nvidia.com/XFree86/Linux-x86_64/$VERSION/$DRIVER_RUN_FILE" && \
    sh ./$DRIVER_RUN_FILE --no-kernel-module --silent --no-network && \
    rm -- $DRIVER_RUN_FILE

RUN CUDA_RUN_FILE=cuda_8.0.44_linux-run && \
    wget --progress=dot:mega "http://sdp-services.kat.ac.za/mirror/developer.nvidia.com/compute/cuda/8.0/prod/local_installers/$CUDA_RUN_FILE" && \
    sh ./$CUDA_RUN_FILE --silent --toolkit && \
    rm -- $CUDA_RUN_FILE

ENV PATH="$PATH:/usr/local/cuda/bin"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64"

USER kat

# Force PyOpenCL not to use OpenCL 2.0 features. Ubuntu 16.04 ships
# opencl-headers, which includes OpenCL 2.0 functions, and on this basis
# PyOpenCL tries to use OpenCL 2.0 functions. But ocl-icd-libopencl1 is an
# ICD with only OpenCL 1.2 support, so there are missing symbols (and actually
# libOpenCL.so.1 is found from CUDA, but that doesn't help because CUDA 8.0
# also only ships 1.2 support).
RUN echo "CL_PRETEND_VERSION = '1.2'" >> ~/.aksetup-defaults.py

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
