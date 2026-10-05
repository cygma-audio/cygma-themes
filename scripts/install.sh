#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
for interpreter in python3 python; do
  if command -v "$interpreter" >/dev/null 2>&1 &&
      "$interpreter" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    exec "$interpreter" "$script_dir/install.py" "$@"
  fi
done
echo 'Cygma requires Python 3.10 or newer.' >&2
exit 1
