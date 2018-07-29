# Base Docker images

This repository containers Dockerfiles to build some base images, from which
other SDP Docker images are built.

## Multi-stage build images

The "new" images are intended to be used for [multi-stage
builds](https://docs.docker.com/develop/develop-images/multistage-build/). To
build a package, a first stage should build from docker-base-build; this image
has compilers, development libraries, a wheel cache of common Python packages,
and some scripts to simplify handling pinning dependencies. The final stage
should be based on docker-base-runtime, and typically just copies and activates
a virtual environment.

## Build order

Because Docker does not entirely support diamond inheritance, the hierarchy is
docker-base-runtime » docker-base-build » docker-base-gpu-build, and
docker-base-gpu-runtime inherits from docker-base-runtime but copies elements
from docker-base-gpu-build. Thus, builds must occur in the order
- docker-base-runtime
- docker-base-build
- docker-base-gpu-build
- docker-base-gpu-runtime
