#!/bin/sh
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
#
# The Dockerfiles under images/ are generated from ressources/templates/ by
# src/main.py, but the build workflow consumes the committed files directly.
# Without this check, a hand edit of a generated file -- or a template change
# that was never regenerated -- goes unnoticed and gets published.
#
# This is the whole test suite of the repository, which is why it is what the
# python-checks caller passes as its `test:` input. It used to be a step
# written inline in test-python.yaml; a script is what a caller can name in one
# line, and what can be run by hand the same way CI runs it.

set -eu

cd "$(dirname "$0")/.."

uv run python3 ./src/main.py

status=0

if [ -n "$(git status --porcelain images/)" ]; then
    echo "images/ is out of date."
    echo "Run: uv run python3 ./src/main.py, then commit images/."
    git status --porcelain images/
    git --no-pager diff -- images/
    status=1
fi

exit "$status"
