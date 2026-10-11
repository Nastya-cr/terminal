#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
export EMU_HOME=/home/student
log_file="${TMPDIR:-/tmp}/shell-emulator-stage2.xml"
./run.sh \
    --vfs examples/vfs.xml \
    --prompt "student$ " \
    --log "$log_file" \
    --startup examples/stage2.txt \
    --headless
