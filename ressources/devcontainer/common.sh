# shellcheck shell=bash
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Sourced by the lifecycle scripts: LOG_TAG names the script in the log, and
# the first argument, or else the cwd, is the workspace, which becomes the
# cwd. devcontainer.json passes ${containerWorkspaceFolder}.

log() {
    echo "[${LOG_TAG}] $*"
}

# Run a command, printing it first and reporting its exit code on failure.
step() {
    local rc=0
    log "\$ $*"
    # Not `if ! "$@"`: $? would then hold the negation's status (0), and the
    # failure would be reported as exit 0 and let the container look healthy.
    "$@" || rc=$?
    if [ "$rc" -ne 0 ]; then
        log "FAILED (exit $rc): $*"
        exit "$rc"
    fi
}

cd "${1:-.}" || exit
log "workspace: $PWD"
