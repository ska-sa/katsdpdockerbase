#!/bin/bash

# Helper for building Docker images on Jenkins. It uses environment
# variables set by Jenkins to affect the build.

set -e
if [ "$#" -lt 1 ]; then
    echo "Usage: build-docker-image.sh [--push-external] image-name [args]" 1>&2
    exit 1
fi
if [ -z "$DOCKER_REGISTRY" ]; then
    echo "DOCKER_REGISTRY is not set" 1>&2
    exit 1
fi
if [ -z "$BRANCH_NAME" ]; then
    echo "BRANCH_NAME is not set" 1>&2
    exit 1
fi
push_external=0
if [ "$1" = "--push-external" ]; then
    if [ -z "$DOCKER_EXTERNAL_REGISTRY" ]; then
        echo "DOCKER_EXTERNAL_REGISTRY must be set when using --push-external" 1>& 2
        exit 1
    fi
    push_external=1
    shift
fi

NAME="$1"
shift
LABEL="${BRANCH_NAME#origin/}"
# Replace characters not legal in Docker tags with underscores
LABEL="$(echo -n "$LABEL" | tr -c '[:alnum:]-.' _)"
if [ "$LABEL" = "master" ]; then
    LABEL=latest
fi
# katversion depends on interrogating git to find the version number, but if
# the directory containing the Dockerfile isn't the top-level directory, or if
# .git is listed in .Dockerignore, then it won't find it. It has a fallback of
# consulting a file called ___version___, so we extract the version from
# outside Docker and create that file. Note that this code needs to work on
# Python 2 and 3.
if [ -n "$VIRTUAL_ENV" ]; then
    pip install katversion
    python -c 'import katversion; print(katversion.get_version())' > ___version___
fi
if [ -x "scripts/docker_build.sh" ]; then
    docker_build="scripts/docker_build.sh"
else
    docker_build="docker build"
fi

declare -a build_args
if grep -q '^ARG KATSDPDOCKERBASE_REGISTRY' Dockerfile; then
    build_args+=(--build-arg "KATSDPDOCKERBASE_REGISTRY=$DOCKER_REGISTRY")
fi
if grep -q '^ARG TAG' Dockerfile; then
    build_args+=(--build-arg "TAG=$LABEL")
fi

$docker_build --label=org.label-schema.schema-version=1.0 \
              --label=org.label-schema.vcs-ref="$(git rev-parse HEAD)" \
              --label=org.label-schema.vcs-url="$(git remote get-url origin)" \
              --label=org.opencontainers.image.revision="$(git rev-parse HEAD)" \
              --label=org.opencontainers.image.source="$(git remote get-url origin)" \
              ${build_args[@]} \
              --pull=true --no-cache=true --force-rm=true \
              -t "$DOCKER_REGISTRY/$NAME:$LABEL" "$@" .
# Remove the image, whether push is successful or not, to avoid accumulating
# more and more images on the build slaves. This is skipped for Jenkins
# images, since they are actually used on the build machines.
if [[ "$NAME" != jenkins-* || "$NAME" != latest ]]; then
    trap "docker rmi $DOCKER_REGISTRY/$NAME:$LABEL" EXIT
fi
rm -f ___version___
docker push "$DOCKER_REGISTRY/$NAME:$LABEL"
if [ "$push_external" -eq 1 ]; then
    trap "docker rmi $DOCKER_EXTERNAL_REGISTRY/$NAME:$LABEL" EXIT
    docker tag "$DOCKER_REGISTRY/$NAME:$LABEL" "$DOCKER_EXTERNAL_REGISTRY/$NAME:$LABEL"
    docker push "$DOCKER_EXTERNAL_REGISTRY/$NAME:$LABEL"
fi
if [ -n "$DOCKER_REGISTRY2" ]; then
    trap "docker rmi $DOCKER_REGISTRY2/$NAME:$LABEL" EXIT
    docker tag "$DOCKER_REGISTRY/$NAME:$LABEL" "$DOCKER_REGISTRY2/$NAME:$LABEL"
    docker push "$DOCKER_REGISTRY2/$NAME:$LABEL"
fi
