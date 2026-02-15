#!/bin/sh
set -eu

# Run from project root inside container.
cd /app

# Ensure coverage CLI is available.
uv sync --group test

# Remove previous HTML report before generating a fresh one.
rm -rf /app/htmlcov/*

# Collect all partial coverage files produced by:
# - FastAPI process (.coverage.fastapi*)
# - pytest process (.coverage.tests*)
files=""
for file in /coverage/.coverage.fastapi* /coverage/.coverage.tests*; do
  if [ -f "$file" ]; then
    files="$files $file"
  fi
done

# Fail clearly if there is nothing to combine.
if [ -z "$files" ]; then
  echo "No coverage data files found in /coverage"
  exit 1
fi

# Merge partial datasets and build final reports.
uv run --project /app coverage combine --data-file=/coverage/.coverage $files
uv run --project /app coverage html --data-file=/coverage/.coverage
uv run --project /app coverage report --data-file=/coverage/.coverage
