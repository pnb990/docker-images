#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Runs at every start of the container, after post-create.sh on the first one:
#   "postStartCommand": "/usr/local/share/devcontainer/post-start.sh ${containerWorkspaceFolder}"
#
# A library holds the coding rules as a clone at the commit its workflows call
# (RG27 of soft-lib/coding-rules): it is cloned once, then moved to that
# commit at every start, so a pull that bumps the pin is followed. A project
# holds them as a submodule, which post-create.sh checks out: nothing to do
# here.

set -e

LOG_TAG=post-start
# shellcheck source-path=SCRIPTDIR
. "$(dirname "$0")/common.sh"

rules=lib_ext/coding-rules
if git ls-files --stage "$rules" | grep -q '^160000'; then
    log "$rules is a submodule: nothing to do"
elif grep -qsE '^[[:space:]-]*uses:[[:space:]]*soft-lib/coding-rules/' \
    .forgejo/workflows/*.yaml .forgejo/workflows/*.yml; then
    if [ ! -e "$rules" ]; then
        step git clone ssh://forgejo@gitbtv.ddns.net:443/soft-lib/coding-rules.git "$rules"
    fi
    step "$rules/setup.sh" --library </dev/null
else
    log "no workflow calls soft-lib/coding-rules: nothing to do"
fi

log "done."
