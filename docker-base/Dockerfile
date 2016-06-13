# Base Dockerfile for SDP images

FROM ubuntu:trusty-20151028

MAINTAINER Bruce Merry "bmerry@ska.ac.za"

# Suppress debconf warnings
ENV DEBIAN_FRONTEND noninteractive

# Install some system packages used by multiple images.
RUN apt-get -y update && apt-get -y install \
    apt-transport-https \
    build-essential pkg-config git-core software-properties-common wget \
    python python-dev libffi-dev libssl-dev python-pip python-virtualenv \
    libboost-python1.55-dev \
    libboost-system1.55-dev \
    gfortran libatlas-dev libblas-dev liblapack-dev \
    libhdf5-dev libfreetype6-dev libpng-dev \
    llvm-3.6-dev libedit-dev

# Install python-casacore build dependencies. Note that this cannot be
# combined into the previous step because apt-add-repository is part of
# software-properties-common, installed above.
RUN add-apt-repository -y ppa:radio-astro/main && \
    add-apt-repository -y 'deb http://za.archive.ubuntu.com/ubuntu/ trusty multiverse' && \
    apt-get -y update && \
    apt-get -y install libcasacore2-dev libcfitsio3-dev

# Install some components of MLNX_OFED
RUN cd /tmp && \
    wget http://www.mellanox.com/downloads/ofed/MLNX_OFED-3.2-2.0.0.0/MLNX_OFED_LINUX-3.2-2.0.0.0-ubuntu14.04-x86_64.tgz && \
    tar -zxf MLNX_OFED_LINUX-3.2-2.0.0.0-ubuntu14.04-x86_64.tgz && \
    echo 'deb file:///tmp/MLNX_OFED_LINUX-3.2-2.0.0.0-ubuntu14.04-x86_64 ./' > /etc/apt/sources.list.d/mlnx-ofed.list && \
    wget -qO - http://www.mellanox.com/downloads/ofed/RPM-GPG-KEY-Mellanox | sudo apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends libibverbs-dev librdmacm-dev libvma-dev && \
    rm -rf /tmp/MLNX_OFED_LINUX-3.2-2.0.0.0-ubuntu14.04-x86_64 /etc/apt/sources.list.d/mlnx-ofed.list

# Install tini (a mini-init) and set it as entrypoint so that we don't
# accumulate zombie processes.
RUN wget https://github.com/krallin/tini/releases/download/v0.9.0/tini -O /sbin/tini && \
    chmod +x /sbin/tini
ENTRYPOINT ["/sbin/tini", "--"]

# Create and switch to a user which will be used to run commands with reduced
# privileges.
RUN adduser --disabled-password --gecos 'unprivileged user' kat
COPY id_rsa /home/kat/.ssh/
# Docker creates all COPY files as root
RUN chown -R kat:kat /home/kat/.ssh
USER kat

# Set up access to github private repositories
RUN echo "Host *\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config
RUN chmod -R go-rwx ~/.ssh

COPY *-requirements.txt /home/kat/docker-base/
COPY install-requirements.py /home/kat/bin/
ENV LLVM_CONFIG="llvm-config-3.6"
# Pre-build a number of wheels to speed up building of dependent images. These
# are all the latest versions at the time of writing.
RUN virtualenv ~/tmp-ve && \
    . ~/tmp-ve/bin/activate && \
    ~/bin/install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    ~/bin/install-requirements.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve

# Create a virtual environment for use in child images
RUN virtualenv ~/ve && \
    . ~/ve/bin/activate && \
    ~/bin/install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    ~/bin/install-requirements.py -d ~/docker-base/base-requirements.txt manhole
# Activate it. We can't use ~/ve/bin/activate, because any environment set in a
# RUN step is lost at the end of the step. We also add ~/bin to PATH so that
# install-requirements.py can be found.
ENV PATH="/home/kat/ve/bin:/home/kat/bin:$PATH" \
    VIRTUAL_ENV="/home/kat/ve"
