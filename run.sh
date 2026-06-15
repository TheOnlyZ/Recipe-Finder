#!/bin/bash
PYTHON_BIN="/tmp/python3_expanded/Python_Framework.pkg/Payload/Versions/3.13/bin/python3.13"
export PYTHONPATH="/Users/zoltanlaszlo/recipe_system:$PYTHONPATH"

case "${1:-api}" in
  scrape)
    echo "=== Running recipe scraper ==="
    exec $PYTHON_BIN -m scraper.pipeline --max-books "${2:-20}"
    ;;
  api)
    echo "=== Starting API server on http://0.0.0.0:8000 ==="
    exec $PYTHON_BIN -m uvicorn backend.main:app --host 0.0.0.0 --port "${2:-8000}" --reload
    ;;
  *)
    echo "Usage: $0 {scrape [max_books]|api [port]}"
    exit 1
    ;;
esac
