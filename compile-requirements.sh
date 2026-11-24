#!/bin/bash
# Compile requirements files from their .in sources.
# Run this whenever any .in file changes, then commit all changed files.
#
# Usage:
#   ./compile-requirements.sh          # compile all
#   ./compile-requirements.sh pre      # compile only pre-requirements
#   ./compile-requirements.sh base     # compile only base-requirements
#   ./compile-requirements.sh gpu      # compile only gpu-requirements

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${SCRIPT_DIR}/docker-base-build"
GPU_DIR="${SCRIPT_DIR}/docker-base-gpu-build"

# Python version used for compiling requirements.
# Change this if the base image Python version changes.
PYTHON_VERSION="3.10"

compile_pre() {
    echo "Compiling pre-requirements.in -> pre-requirements.txt..."
    uv pip compile \
        --python-version "${PYTHON_VERSION}" \
        "${BASE_DIR}/pre-requirements.in" \
        -o "${BASE_DIR}/pre-requirements.txt"
    echo "Done: pre-requirements.txt"
}

compile_base() {
    echo "Compiling base-requirements.in -> base-requirements.txt..."
    uv pip compile \
        --python-version "${PYTHON_VERSION}" \
        "${BASE_DIR}/base-requirements.in" \
        -o "${BASE_DIR}/base-requirements.txt"
    echo "Done: base-requirements.txt"
}

compile_gpu() {
    echo "Compiling GPU requirements.in -> GPU requirements.txt..."
    uv pip compile \
        --python-version "${PYTHON_VERSION}" \
        --no-binary pycuda \
        --constraint "${BASE_DIR}/base-requirements.txt" \
        "${GPU_DIR}/requirements.in" \
        -o "${GPU_DIR}/requirements.txt"
    echo "Done: GPU requirements.txt"
}

TARGET="${1:-all}"

case "$TARGET" in
    pre)  compile_pre ;;
    base) compile_base ;;
    gpu)  compile_gpu ;;
    all)
        compile_pre
        compile_base
        compile_gpu
        ;;
    *)
        echo "Unknown target: $TARGET"
        echo "Usage: $0 [pre|base|gpu|all]"
        exit 1
        ;;
esac

echo ""
echo "Commit all changed files to the repository."
