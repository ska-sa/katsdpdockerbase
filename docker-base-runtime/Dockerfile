# A temporary stage just to compile schedrr
FROM ubuntu:bionic-20190807 as build-schedrr
RUN apt-get -y update && apt-get -y install gcc
# Create a setuid binary to assist with realtime scheduling
COPY schedrr.c /usr/local/src
RUN gcc -o /usr/local/bin/schedrr /usr/local/src/schedrr.c -Wall -Wextra -s -O2

#######################################################################

FROM ubuntu:bionic-20190807
LABEL maintainer="sdpdev+katsdpdockerbase@ska.ac.za"

# Suppress debconf warnings
ENV DEBIAN_FRONTEND noninteractive

# Install some system packages used by multiple images.
# (netbase installs /etc/services and /etc/protocols, which some packages
# fail without).
RUN apt-get -y update && apt-get --no-install-recommends -y install \
        apt-transport-https gpg-agent \
        software-properties-common wget curl \
        python python3 virtualenv \
        libboost-program-options1.65 \
        libboost-python1.65 \
        libboost-system1.65 \
        libboost-regex1.65 \
        netbase && \
    rm -rf /var/lib/apt/lists/*

# Install python-casacore run-time dependencies. Note that this cannot be
# combined into the previous step because apt-add-repository is part of
# software-properties-common, installed above.
RUN add-apt-repository -y ppa:kernsuite/kern-5 && \
    apt-get -y update && \
    apt-get --no-install-recommends -y install \
        casacore-data && \
    rm -rf /var/lib/apt/lists/*

COPY mirror_wget /usr/local/bin/mirror_wget
ARG KATSDPDOCKERBASE_MIRROR=http://sdp-services.kat.ac.za/mirror

# Install some components of MLNX_OFED
ENV MLNX_OFED_VERSION=4.7-1.0.0.1
RUN cd /tmp && \
    MLNX_OFED_PATH=MLNX_OFED_LINUX-$MLNX_OFED_VERSION-ubuntu18.04-x86_64 && \
    mirror_wget --progress=dot:mega https://www.mellanox.com/downloads/ofed/MLNX_OFED-$MLNX_OFED_VERSION/$MLNX_OFED_PATH.tgz && \
    tar -zxf $MLNX_OFED_PATH.tgz && \
    echo "deb file:///tmp/$MLNX_OFED_PATH/DEBS/MLNX_LIBS ./" > /etc/apt/sources.list.d/mlnx-ofed.list && \
    mirror_wget -qO - https://www.mellanox.com/downloads/ofed/RPM-GPG-KEY-Mellanox | apt-key add - && \
    apt-get -y update && \
    apt-get install -y --no-install-recommends \
        libibverbs1 librdmacm1 libmlx4-1 libmlx5-1 && \
    rm -rf "/tmp/$MLNX_OFED_PATH" \
        "/tmp/$MLNX_OFED_PATH.tgz" \
        /etc/apt/sources.list.d/mlnx-ofed.list \
        /var/lib/apt/lists/* \
        /tmp/vma

# Install tini (a mini-init) and set it as entrypoint so that we don't
# accumulate zombie processes.
RUN mirror_wget https://github.com/krallin/tini/releases/download/v0.18.0/tini -O /sbin/tini && \
    chmod +x /sbin/tini
ENTRYPOINT ["/sbin/tini", "--"]

# Create a setuid binary to assist with realtime scheduling
COPY --from=build-schedrr /usr/local/bin/schedrr /usr/local/bin/schedrr
RUN chmod u+s /usr/local/bin/schedrr
# A helper script to run a program then clean up its scratch space
COPY run-and-cleanup /usr/local/bin/run-and-cleanup

# Create and switch to a user which will be used to run commands with reduced
# privileges.
RUN adduser --disabled-password --gecos 'unprivileged user' kat
USER kat

# Define environment variables that child images can copy to PATH and
# VIRTUAL_ENV to activate a virtual environment.
ENV PATH_PYTHON3="/home/kat/ve3/bin:$PATH" \
    PATH_PYTHON2="/home/kat/ve/bin:$PATH" \
    VIRTUAL_ENV_PYTHON2="/home/kat/ve" \
    VIRTUAL_ENV_PYTHON3="/home/kat/ve3"
