#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
if ./run.sh \
    --vfs examples/vfs.xml \
    --log "${TMPDIR:-/tmp}/shell-emulator-stage4.xml" \
    --startup examples/stage4.txt \
    --headless; then
    echo "Ожидалась тестовая ошибка" >&2
    exit 1
fi
echo "Стартовый скрипт правильно остановился на первой ошибке"
