FROM sdp-docker-registry.kat.ac.za:5000/docker-base-runtime
MAINTAINER Bruce Merry "bmerry@ska.ac.za"

USER root

RUN apt-get -y update && apt-get --no-install-recommends -y install \
    build-essential pkg-config git-core ssh \
    python-dev python3-dev \
    libboost-program-options-dev \
    libboost-python-dev \
    libboost-system-dev \
    libboost-regex-dev \
    libeigen3-dev \
    autoconf automake \
    casacore-dev libcfitsio-dev wcslib-dev

# Install dev libraries from MLNX OFED
RUN cd /tmp && \
    MLNX_OFED_PATH=MLNX_OFED_LINUX-$MLNX_OFED_VERSION-ubuntu16.04-x86_64 && \
    wget --progress=dot:mega http://sdp-services.kat.ac.za/mirror/www.mellanox.com/downloads/ofed/MLNX_OFED-$MLNX_OFED_VERSION/$MLNX_OFED_PATH.tgz && \
    tar -zxf $MLNX_OFED_PATH.tgz && \
    echo "deb file:///tmp/$MLNX_OFED_PATH/DEBS ./" > /etc/apt/sources.list.d/mlnx-ofed.list && \
    wget -qO - http://sdp-services.kat.ac.za/mirror/www.mellanox.com/downloads/ofed/RPM-GPG-KEY-Mellanox | apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libibverbs-dev librdmacm-dev libvma-dev && \
    rm -rf "/tmp/$MLNX_OFED_PATH" \
        "/tmp/$MLNX_OFED_PATH.tgz" \
        /etc/apt/sources.list.d/mlnx-ofed.list \
        /var/lib/apt/lists/*

# Install git-lfs
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash && \
    apt-get install git-lfs

USER kat

# Set up access to github private repositories and set up git-lfs
COPY --chown=kat:kat id_rsa /home/kat/.ssh/
RUN echo "Host *\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config && \
    chmod -R go-rwx ~/.ssh && \
    git lfs install --skip-smudge

COPY --chown=kat:kat *-requirements.txt /home/kat/docker-base/
COPY install-requirements.py /usr/local/bin/
# Pre-build a number of wheels to speed up building of dependent images.
RUN virtualenv ~/tmp-ve && \
    . ~/tmp-ve/bin/activate && \
    install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve
# Same again for Python 3
RUN virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    install-requirements.py -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve3

# Create empty virtual environments for child images to install to
RUN virtualenv ~/ve && \
    . ~/ve/bin/activate && \
    install-requirements.py -r ~/docker-base/pre-requirements.txt
RUN virtualenv -p /usr/bin/python3 ~/ve3 && \
    . ~/ve3/bin/activate && \
    install-requirements.py -r ~/docker-base/pre-requirements.txt
