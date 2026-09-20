#!/bin/sh
exec python3 -m uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8080}"
