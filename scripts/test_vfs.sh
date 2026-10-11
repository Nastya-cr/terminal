#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
for vfs in vfs_minimal.xml vfs.xml vfs_deep.xml; do
    ./run.sh \
        --vfs "examples/$vfs" \
        --log "${TMPDIR:-/tmp}/$vfs-log.xml" \
        --startup examples/stage3.txt \
        --headless
done
