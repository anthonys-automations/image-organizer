#!/bin/bash

# Development script for image-organizer
# Runs linting, type checking, and tests

set -e

echo "🧹 Running linting..."
ruff check .

echo "🎨 Running code formatting check..."
black --check .

echo "🔍 Running type checking..."
mypy imgtool/

echo "🧪 Running tests..."
pytest -q --cov=imgtool tests/

echo "✅ All checks passed!" 