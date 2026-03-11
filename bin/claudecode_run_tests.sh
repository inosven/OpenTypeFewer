#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"

mkdir -p "$LOG_DIR"

DATE_STAMP=$(date +%Y%m%d)

SKIP_HARDWARE=""

for arg in "$@"; do
    if [ "$arg" = "--no-hardware" ]; then
        SKIP_HARDWARE="-m not hardware"
        shift
        break
    fi
done

if [ -z "$1" ]; then
    LOG_FILE="$LOG_DIR/test_all_${DATE_STAMP}.log"
    echo "Running all tests..."
    cd "$PROJECT_DIR"
    python -m pytest tests/ -v $SKIP_HARDWARE 2>&1 | tee "$LOG_FILE"
else
    TEST_ID="$1"
    LOG_FILE="$LOG_DIR/test_${TEST_ID}_${DATE_STAMP}.log"
    echo "Running test $TEST_ID..."
    cd "$PROJECT_DIR"
    python -m pytest tests/*/"$TEST_ID"/ -v $SKIP_HARDWARE 2>&1 | tee "$LOG_FILE"
fi
