#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
./scripts/test_parameters.sh
./scripts/test_vfs.sh
./scripts/test_commands.sh
./scripts/test_mutating_commands.sh
