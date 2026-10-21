#!/bin/sh
# Dispatch: report | selftest | pricelist | web
set -e
cmd="${1:-web}"
[ $# -gt 0 ] && shift
case "$cmd" in
  report)    exec python jyotisha_report.py "$@" ;;
  selftest)  exec python jyotisha_calc.py --selftest ;;
  pricelist) exec python jyotisha_pricelist.py "$@" ;;
  web)       exec uvicorn web.app:app --host 0.0.0.0 --port "${PORT:-8000}" ;;
  *)         echo "usage: report <args> | selftest | pricelist <args> | web" >&2; exit 2 ;;
esac
