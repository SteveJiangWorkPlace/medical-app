#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt
python scripts/ensure_pgvector.py
alembic upgrade head
