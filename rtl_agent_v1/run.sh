#!/usr/bin/env bash
# RTL Agent V1 Execution Entry Point
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${HERE}:${PYTHONPATH:-}"

exec python3 -m agent.main "$@"
