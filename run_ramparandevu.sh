#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR/backend"

export PYTHONPATH="$DIR/backend"
echo "======================================================="
echo "   RAMPARANDEVU - YARD & DOCK MANAGEMENT SYSTEM"
echo "   Dinamik Tesis & Saha Yönetimi - Port: 8080"
echo "======================================================="

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
