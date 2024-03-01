ARG KATSDPDOCKERBASE_REGISTRY=harbor.sdp.kat.ac.za/dpp
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

# Install git-lfs
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash && \
    apt-get install git-lfs

USER kat

# Set up git-lfs and include github host key for downstream users who may want to use SSH access
RUN mkdir ~/.ssh && \
    echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=" >> ~/.ssh/known_hosts && \
    chmod -R go-rwx ~/.ssh && \
    git lfs install --skip-smudge

COPY --chown=kat:kat *-requirements.txt /home/kat/docker-base/
COPY install-requirements.py /usr/local/bin/
COPY install_pinned.py /usr/local/bin
# Pre-build a number of wheels to speed up building of dependent images.
RUN virtualenv -p /usr/bin/python3 ~/tmp-ve3 && \
    . ~/tmp-ve3/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt && \
    install_pinned.py -r ~/docker-base/base-requirements.txt && \
    rm -r ~/tmp-ve3

# Create empty virtual environment for child images to install to
RUN virtualenv -p /usr/bin/python3 ~/ve3 && \
    . ~/ve3/bin/activate && \
    pip install -r ~/docker-base/pre-requirements.txt
