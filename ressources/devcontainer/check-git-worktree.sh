#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
#
# First step of post-create.sh, and runnable by hand from the workspace.
#
# The container mounts the parent of the workspace, so the main clone and
# every sibling worktree keep the same relative layout as on the host. That
# only works with relative-path worktree links (worktree.useRelativePaths): an
# absolute link names a host path that does not exist in the container. The
# container still starts, but its creation fails here, saying what to run.
#
# An absolute link cannot be told apart from a stale one in here, since
# neither resolves. Both are fixed on the host, from the main clone:
#   git worktree repair --relative-paths   # the worktree still exists
#   git worktree prune                     # its directory was deleted

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_TAG=check-git-worktree
# shellcheck source-path=SCRIPTDIR
. "$SCRIPT_DIR/common.sh"

status=0

error() {
    log "ERROR: $*" >&2
    status=1
}

# ~/.gitconfig is the host's, bind-mounted: this also covers worktrees
# created on the host later.
if [ "$(git config --global --type=bool --get worktree.useRelativePaths)" \
    != "true" ]; then
    error "worktree.useRelativePaths is not enabled, run on the host:" \
        "git config --global worktree.useRelativePaths true"
fi

# Read by hand rather than through git: with an absolute link, git cannot
# open the workspace at all.
if [ -f .git ]; then
    target="$(sed -e 's/^gitdir: //' .git)"
    if [[ "${target}" == /* ]]; then
        error "absolute worktree link in $WORKSPACE_DIR/.git (${target})," \
            "run on the host from the main clone:" \
            "git worktree repair --relative-paths"
        exit "$status"
    fi
fi

# The back-link of every worktree of the repository: an absolute one would
# also make a `git worktree prune` run in here drop that worktree.
common_dir="$(git rev-parse --path-format=absolute --git-common-dir)"
for gitdir_file in "${common_dir}"/worktrees/*/gitdir; do
    if [ -f "${gitdir_file}" ]; then
        target="$(cat "${gitdir_file}")"
        if [[ "${target}" == /* ]]; then
            error "absolute or stale worktree entry ${gitdir_file}" \
                "(${target}), run on the host from the main clone:" \
                "git worktree repair --relative-paths, or" \
                "git worktree prune if that worktree was deleted"
        fi
    fi
done

exit "$status"
