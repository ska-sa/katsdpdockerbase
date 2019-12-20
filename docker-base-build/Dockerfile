ARG KATSDPDOCKERBASE_REGISTRY=sdp-docker-registry.kat.ac.za:5000
ARG TAG=latest

FROM $KATSDPDOCKERBASE_REGISTRY/docker-base-runtime:$TAG
LABEL maintainer="sdpdev+katsdpdockerbase@ska.ac.za"

USER root

RUN apt-get -y update && apt-get --no-install-recommends -y install \
    build-essential pkg-config git-core ssh \
    python3-dev \
    libboost-program-options-dev \
    libboost-python-dev \
    libboost-system-dev \
    libboost-regex-dev \
    libeigen3-dev \
    autoconf automake \
    casacore-dev libcfitsio-dev wcslib-dev

ARG KATSDPDOCKERBASE_MIRROR=http://sdp-services.kat.ac.za/mirror

# Install dev libraries from MLNX OFED
RUN cd /tmp && \
    MLNX_OFED_PATH=MLNX_OFED_LINUX-$MLNX_OFED_VERSION-ubuntu18.04-x86_64 && \
    mirror_wget --progress=dot:mega https://www.mellanox.com/downloads/ofed/MLNX_OFED-$MLNX_OFED_VERSION/$MLNX_OFED_PATH.tgz && \
    tar -zxf $MLNX_OFED_PATH.tgz && \
    echo "deb file:///tmp/$MLNX_OFED_PATH/DEBS/MLNX_LIBS ./" > /etc/apt/sources.list.d/mlnx-ofed.list && \
    mirror_wget -qO - https://www.mellanox.com/downloads/ofed/RPM-GPG-KEY-Mellanox | apt-key add - && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libibverbs-dev librdmacm-dev && \
    rm -rf "/tmp/$MLNX_OFED_PATH" \
        "/tmp/$MLNX_OFED_PATH.tgz" \
        /etc/apt/sources.list.d/mlnx-ofed.list \
        /var/lib/apt/lists/* \
        /tmp/vma

# Install git-lfs
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash && \
    apt-get install git-lfs

USER kat

# Set up git-lfs and include github host key for downstream users who may want to use SSH access
RUN mkdir ~/.ssh && \
    echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" >> ~/.ssh/known_hosts && \
    chmod -R go-rwx ~/.ssh && \
    git lfs install --skip-smudge

COPY --chown=kat:kat *-requirements.txt /home/kat/docker-base/
COPY install-requirements.py /usr/local/bin/
# Pre-build a number of wheels to speed up building of dependent images.
RUN virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt && \
    install-requirements.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve3

# Create empty virtual environment for child images to install to
RUN virtualenv -p /usr/bin/python3 ~/ve3 && \
    . ~/ve3/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt
