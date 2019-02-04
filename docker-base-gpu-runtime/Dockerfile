FROM sdp-docker-registry.kat.ac.za:5000/docker-base-runtime
MAINTAINER Bruce Merry "bmerry@ska.ac.za"

USER root

# CUDA expects g++ even if only compiling for GPU
RUN apt-get -y update && apt-get install --no-install-recommends -y \
        g++ ocl-icd-libopencl1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=sdp-docker-registry.kat.ac.za:5000/docker-base-gpu-build /usr/local/cuda-10.0 /usr/local/cuda-10.0
RUN ln -s /usr/local/cuda-10.0 /usr/local/cuda

ENV PATH="$PATH:/usr/local/cuda/bin" \
    PATH_PYTHON2="$PATH_PYTHON2:/usr/local/cuda/bin" \
    PATH_PYTHON3="$PATH_PYTHON3:/usr/local/cuda/bin"
# /usr/lib/x86_64-linux-gnu is explicitly added to the front to prevent the
# CUDA version of libOpenCL.so.1 (which is older) from overriding the version
# installed by ocl-icd-opencl-dev.
ENV LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/local/cuda/lib64"

# Create information for locating the NVIDIA driver components. This isn't handled
# by nvidia-docker.
RUN mkdir -p /etc/OpenCL/vendors && \
    echo libnvidia-opencl.so.1 > /etc/OpenCL/vendors/nvidia.icd

USER kat

# For nvidia-docker 1.0
LABEL com.nvidia.volumes.needed="nvidia_driver" com.nvidia.cuda.version="10.0"
# For nvidia-container-runtime
ENV NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility NVIDIA_REQUIRE_CUDA=cuda>=10.0
