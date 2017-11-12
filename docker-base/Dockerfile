# Base Dockerfile for SDP images

FROM ubuntu:xenial-20161010

MAINTAINER Bruce Merry "bmerry@ska.ac.za"

# Suppress debconf warnings
ENV DEBIAN_FRONTEND noninteractive

# Install some system packages used by multiple images.
RUN apt-get -y update && apt-get -y install \
    apt-transport-https \
    build-essential pkg-config git-core software-properties-common wget curl \
    python python-dev libffi-dev libssl-dev python-pip python-virtualenv \
    python3 python3-dev python3-pip python3-virtualenv \
    libboost-program-options-dev \
    libboost-python-dev \
    libboost-system-dev \
    libboost-regex-dev \
    libeigen3-dev \
    gfortran libatlas-dev libblas-dev liblapack-dev \
    libhdf5-dev libfreetype6-dev libpng-dev \
    llvm-dev libedit-dev \
    autoconf automake

# Install python-casacore build dependencies. Note that this cannot be
# combined into the previous step because apt-add-repository is part of
# software-properties-common, installed above.
RUN add-apt-repository -y ppa:kernsuite/kern-2 && \
    add-apt-repository -y multiverse && \
    apt-get -y update && \
    apt-get -y install casacore-dev libcfitsio3-dev wcslib-dev

# Install some components of MLNX_OFED
RUN cd /tmp && \
    wget --progress=dot:mega http://sdp-services.kat.ac.za/mirror/www.mellanox.com/downloads/ofed/MLNX_OFED-4.1-1.0.2.0/MLNX_OFED_LINUX-4.1-1.0.2.0-ubuntu16.04-x86_64.tgz && \
    tar -zxf MLNX_OFED_LINUX-4.1-1.0.2.0-ubuntu16.04-x86_64.tgz && \
    echo 'deb file:///tmp/MLNX_OFED_LINUX-4.1-1.0.2.0-ubuntu16.04-x86_64/DEBS ./' > /etc/apt/sources.list.d/mlnx-ofed.list && \
    wget -qO - http://sdp-services.kat.ac.za/mirror/www.mellanox.com/downloads/ofed/RPM-GPG-KEY-Mellanox | apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libibverbs-dev librdmacm-dev libvma-dev libmlx4-1 && \
    rm -rf /tmp/MLNX_OFED_LINUX-4.1-1.0.2.0-ubuntu16.04-x86_64 \
        /tmp/MLNX_OFED_LINUX-4.1-1.0.2.0-ubuntu16.04-x86_64.tgz \
        /etc/apt/sources.list.d/mlnx-ofed.list

# Install git-lfs
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash && \
    apt-get install git-lfs

# Install tini (a mini-init) and set it as entrypoint so that we don't
# accumulate zombie processes.
RUN wget http://sdp-services.kat.ac.za/mirror/github.com/krallin/tini/releases/download/v0.10.0/tini -O /sbin/tini && \
    chmod +x /sbin/tini
ENTRYPOINT ["/sbin/tini", "--"]

# Create a setuid binary to assist with realtime scheduling
COPY schedrr.c /usr/local/src
RUN gcc -o /usr/local/bin/schedrr /usr/local/src/schedrr.c -Wall -Wextra -s -O2 && \
    chmod u+s /usr/local/bin/schedrr

# Create and switch to a user which will be used to run commands with reduced
# privileges.
RUN adduser --disabled-password --gecos 'unprivileged user' kat
COPY id_rsa /home/kat/.ssh/
# Docker creates all COPY files as root
RUN chown -R kat:kat /home/kat/.ssh
USER kat

# Set up access to github private repositories and set up git-lfs
# git lfs install has a bug (https://github.com/github/git-lfs/issues/1231)
# that makes it create a 'lfs' subdirectory. We let it create it in /tmp and
# then delete it again.
RUN echo "Host *\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config && \
    chmod -R go-rwx ~/.ssh && \
    cd /tmp && git lfs install --skip-smudge && rm -rf lfs

COPY *-requirements.txt /home/kat/docker-base/
COPY install-requirements.py /home/kat/bin/
# Pre-build a number of wheels to speed up building of dependent images. These
# are all the latest versions at the time of writing.
RUN virtualenv ~/tmp-ve && \
    . ~/tmp-ve/bin/activate && \
    ~/bin/install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    ~/bin/install-requirements.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve
# Same against for Python 3
RUN virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    ~/bin/install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    ~/bin/install-requirements.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve3

# Create virtual environments for use in child images
RUN virtualenv ~/ve && \
    . ~/ve/bin/activate && \
    ~/bin/install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    ~/bin/install-requirements.py -d ~/docker-base/base-requirements.txt manhole
RUN virtualenv -p /usr/bin/python3 ~/ve3 && \
    . ~/ve3/bin/activate && \
    ~/bin/install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    ~/bin/install-requirements.py -d ~/docker-base/base-requirements.txt manhole
# Activate the Python 2 environment. We can't use ~/ve/bin/activate, because
# any environment set in a RUN step is lost at the end of the step. We also add
# ~/bin to PATH so that install-requirements.py can be found.
ENV PATH_PYTHON3="/home/kat/ve3/bin:/home/kat/bin:$PATH" \
    PATH="/home/kat/ve/bin:/home/kat/bin:$PATH" \
    VIRTUAL_ENV="/home/kat/ve" \
    VIRTUAL_ENV_PYTHON3="/home/kat/ve3"
