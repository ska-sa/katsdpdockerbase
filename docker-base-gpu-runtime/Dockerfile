ARG KATSDPDOCKERBASE_REGISTRY=harbor.sdp.kat.ac.za/dpp
ARG TAG=latest

# Just to give it a name to refer to for the later COPY step
FROM $KATSDPDOCKERBASE_REGISTRY/docker-base-gpu-build:$TAG as gpu-build

FROM $KATSDPDOCKERBASE_REGISTRY/docker-base-runtime:$TAG
LABEL maintainer="sdpdev+katsdpdockerbase@ska.ac.za"

USER root

# CUDA expects g++ even if only compiling for GPU
RUN apt-get -y update && apt-get install --no-install-recommends -y \
        g++ ocl-icd-libopencl1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=gpu-build /usr/local/cuda-11.4 /usr/local/cuda-11.4
RUN ln -s /usr/local/cuda-11.4 /usr/local/cuda

ENV PATH="$PATH:/usr/local/cuda/bin" \
    PATH_PYTHON3="$PATH_PYTHON3:/usr/local/cuda/bin"
# Calling the file z_cuda puts it behind the system libraries in search
# order, which ensures that the system version of libOpenCL.so.1 (which is
# newer) is found in preference to the one provided with CUDA).
RUN echo '/usr/local/cuda/lib64' > /etc/ld.so.conf.d/z_cuda.conf && ldconfig

# Create information for locating the NVIDIA driver components. This isn't handled
# by nvidia-container-runtime.
RUN mkdir -p /etc/OpenCL/vendors && \
    echo libnvidia-opencl.so.1 > /etc/OpenCL/vendors/nvidia.icd

USER kat

# For nvidia-container-runtime
ENV NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility NVIDIA_REQUIRE_CUDA=cuda>=11.4

# Just so that if the user passes the --build-arg they don't get a warning
ARG KATSDPDOCKERBASE_MIRROR=http://sdp-services.kat.ac.za/mirror
