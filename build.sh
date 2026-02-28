#!/usr/bin/env bash
# build.sh — Render build script for spotter-api
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput


