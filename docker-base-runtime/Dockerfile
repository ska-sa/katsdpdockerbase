# A temporary stage just for compiling things
FROM ubuntu:focal-20201106 as build
RUN apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y install \
    wget \
    build-essential cmake gcc libudev-dev libnl-3-dev libnl-route-3-dev \
    ninja-build pkg-config valgrind python3-dev cython3 python3-docutils pandoc \
    libcap-dev

# Create a setuid binary to assist with realtime scheduling
COPY schedrr.c /usr/local/src
RUN gcc -o /usr/local/bin/schedrr /usr/local/src/schedrr.c -Wall -Wextra -s -O2

# Create a utility to allow increasing privileges where needed. Individual
# containers should use 'setcap /usr/local/bin/capambel cap_xxx+i' to grant
# the necessary privileges (and also run Docker with --cap-add where
# necessary).
COPY capambel.c /usr/local/src
RUN gcc -o /usr/local/bin/capambel /usr/local/src/capambel.c -Wall -Wextra -s -O2 -lcap

# Install rdma-core. The steps are loosely based on the rdma-core README.md and
# debian/rules.
WORKDIR /tmp
RUN wget https://github.com/linux-rdma/rdma-core/releases/download/v31.0/rdma-core-31.0.tar.gz
RUN tar -zxf rdma-core-31.0.tar.gz && \
    mkdir rdma-core-31.0/build && \
    cd rdma-core-31.0/build && \
    cmake \
        -GNinja \
        -DDISTRO_FLAVOUR=Debian \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX:PATH=/usr \
        -DCMAKE_INSTALL_SYSCONFDIR:PATH=/etc \
        -DCMAKE_INSTALL_SYSTEMD_SERVICEDIR:PATH=/lib/systemd/system \
        -DCMAKE_INSTALL_INITDDIR:PATH=/etc/init.d \
        -DCMAKE_INSTALL_LIBEXECDIR:PATH=/usr/lib \
        -DCMAKE_INSTALL_SHAREDSTATEDIR:PATH=/var/lib \
        -DCMAKE_INSTALL_RUNDIR:PATH=/run \
        -DCMAKE_INSTALL_UDEV_RULESDIR:PATH=/lib/udev/rules.d \
        -DCMAKE_INSTALL_PERLDIR:PATH=/usr/share/perl5 \
        -DNO_PYVERBS=1 \
        .. && \
    DESTDIR=/tmp/rdma-core ninja install

#######################################################################

FROM ubuntu:focal-20201106
LABEL maintainer="sdpdev+katsdpdockerbase@ska.ac.za"

# Suppress debconf warnings
ENV DEBIAN_FRONTEND noninteractive

# Install some system packages used by multiple images.
# (netbase installs /etc/services and /etc/protocols, which some packages
# fail without).
# libtbb is needed due to https://github.com/numba/numba/issues/6108
RUN apt-get -y update && apt-get --no-install-recommends -y install \
        apt-transport-https gpg-agent \
        software-properties-common wget curl \
        python3 virtualenv \
        libboost-program-options1.71.0 \
        libboost-python1.71.0 \
        libboost-system1.71.0 \
        libboost-regex1.71.0 \
        netbase \
        libcap2 \
        libcap2-bin \
        libnl-3-200 libnl-route-3-200 \
        libtbb2 \
        casacore-data && \
    rm -rf /var/lib/apt/lists/*

COPY mirror_wget /usr/local/bin/mirror_wget
ARG KATSDPDOCKERBASE_MIRROR=http://sdp-services.kat.ac.za/mirror

# Install tini (a mini-init) and set it as entrypoint so that we don't
# accumulate zombie processes.
RUN mirror_wget https://github.com/krallin/tini/releases/download/v0.18.0/tini -O /sbin/tini && \
    chmod +x /sbin/tini
ENTRYPOINT ["/sbin/tini", "--"]

# Create a setuid binary to assist with realtime scheduling
COPY --from=build /usr/local/bin/schedrr /usr/local/bin/schedrr
RUN chmod u+s /usr/local/bin/schedrr
# A helper for gaining Linux capabilities
COPY --from=build /usr/local/bin/capambel /usr/local/bin/capambel
# A helper script to run a program then clean up its scratch space
COPY run-and-cleanup /usr/local/bin/run-and-cleanup
# Install rdma-core from build image
# We have to copy each subdirectory individually, because the 20.04 image
# symlinks /lib -> /usr/lib etc, and https://github.com/moby/moby/issues/41035
# causes the symlinks to be overwritten if we try to copy to the root.
COPY --from=build /tmp/rdma-core/etc /etc
COPY --from=build /tmp/rdma-core/lib /lib
COPY --from=build /tmp/rdma-core/usr /usr

# Create and switch to a user which will be used to run commands with reduced
# privileges.
RUN adduser --disabled-password --gecos 'unprivileged user' kat
USER kat

# Define environment variables that child images can copy to PATH and
# VIRTUAL_ENV to activate a virtual environment.
ENV PATH_PYTHON3="/home/kat/ve3/bin:$PATH" \
    VIRTUAL_ENV_PYTHON3="/home/kat/ve3"
