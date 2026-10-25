#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Runs once, right after the container is created:
#   "postCreateCommand": "/usr/local/share/devcontainer/post-create.sh ${containerWorkspaceFolder}"
#
# It only holds what every devcontainer shares. A repository's own steps go
# in .devcontainer/project-install.sh, sourced at the end when it exists: it
# can use log/step, and the cwd is the workspace.
#
# Each step is echoed before it runs, so the devcontainer creation log shows
# exactly which one failed. To debug, run it by hand in the container.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_TAG=post-create
# shellcheck source-path=SCRIPTDIR
. "$SCRIPT_DIR/common.sh"

# First: with an absolute worktree link, git fails in every step below.
step "$SCRIPT_DIR/check-git-worktree.sh"

# XDG_RUNTIME_DIR comes from runArgs in devcontainer.json; keep a fallback so
# the script also works when run by hand.
XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-dev}"
step mkdir -p "$XDG_RUNTIME_DIR"
step chmod 700 "$XDG_RUNTIME_DIR"

# Wire Claude Code's login/config into the persistent volume before any
# extension can start reading/writing ~/.claude or ~/.claude.json.
step "$SCRIPT_DIR/persist-claude-config.sh"

# Before project-install.sh: uv installs some dependencies from lib_ext/
# submodules, and fails on a submodule that is not checked out.
step git submodule update --init

if [ -f "$WORKSPACE_DIR/.devcontainer/project-install.sh" ]; then
    # shellcheck source=/dev/null
    . "$WORKSPACE_DIR/.devcontainer/project-install.sh"
fi

log "done."
