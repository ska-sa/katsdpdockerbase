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

compile_pre() {
    echo "Compiling pre-requirements.in -> pre-requirements.txt..."
    uv pip compile \
        --python-version 3.10 \
        "${BASE_DIR}/pre-requirements.in" \
        -o "${BASE_DIR}/pre-requirements.txt"
    echo "Done: pre-requirements.lock"
}

compile_base() {
    echo "Compiling base-requirements.in -> base-requirements.txt..."
    uv pip compile \
        --python-version 3.10 \
        --no-binary pycuda \
        "${BASE_DIR}/base-requirements.in" \
        -o "${BASE_DIR}/base-requirements.txt"
    echo "Done: base-requirements.txt"
}

compile_gpu() {
    echo "Compiling requirements.in -> gpu-requirements.txt..."
    uv pip compile \
        --python-version 3.10 \
        --no-binary pycuda \
        --constraint "${BASE_DIR}/base-requirements.txt" \
        "${GPU_DIR}/gpu-requirements.in" \
        -o "${GPU_DIR}/gpu-requirements.txt"
    echo "Done: gpu-requirements.txt"
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
