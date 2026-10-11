#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
before="$(cksum examples/vfs.xml)"
if ./run.sh \
    --vfs examples/vfs.xml \
    --log "${TMPDIR:-/tmp}/shell-emulator-stage5.xml" \
    --startup examples/stage5.txt \
    --headless; then
    echo "Ожидалась ошибка удаления непустого каталога" >&2
    exit 1
fi
after="$(cksum examples/vfs.xml)"
test "$before" = "$after"
echo "Исходный XML не изменён"
