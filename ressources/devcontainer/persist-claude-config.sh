#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
#
# Claude Code keeps its login session (~/.claude/.credentials.json) and its
# config/MCP/cache file (~/.claude.json) in the container's writable layer,
# which a rebuild throws away -> re-login and re-onboarding every time.
# This moves both into the "claude-code-config" Docker volume (mounted at
# /home/dev/.claude-persist, which does survive rebuilds) and replaces the
# originals with symlinks, so Claude Code keeps reading/writing the same
# paths without noticing anything moved.
#
# devcontainer.json wiring:
#   mounts: "source=claude-code-config,target=/home/dev/.claude-persist,type=volume"
#   ($HOME below: the script runs as that user)
#   postCreateCommand calls this via post-create.sh

set -e

PERSIST_DIR="$HOME/.claude-persist"

# Docker creates a named volume empty and owned by root when the image carries
# no content at the mount point -- which is the case here. The dev user then
# cannot write into it, the symlinks below end up dangling, and Claude Code
# fails to create .credentials.json: no login ever persists. Reclaim the mount
# point once, before anything tries to write through it.
if [ ! -w "$PERSIST_DIR" ]; then
    sudo chown "$(id -u):$(id -g)" "$PERSIST_DIR"
fi
mkdir -p "$PERSIST_DIR"

# Move $1 into the persist dir (first run) or drop it (later runs, since the
# persisted copy is already authoritative), then symlink it back into place.
# $3 is "dir" or "json": it says what to create when neither side exists yet,
# because `mkdir ~/.claude` on a dangling symlink fails with EEXIST instead of
# creating the store. A seeded json file holds `{}` rather than being empty,
# which Claude Code would report as a corrupt config.
# Idempotent: a no-op once $1 is a symlink that resolves.
persist() {
    local target="$1" stored="$PERSIST_DIR/$2" kind="$3"

    # -L alone is not enough: a run where the volume was not writable leaves a
    # dangling symlink behind, and that one has to be redone.
    if ! { [ -L "$target" ] && [ -e "$target" ]; }; then
        if [ -L "$target" ]; then
            rm -f "$target"
        fi

        if [ -e "$stored" ]; then
            rm -rf "$target"
        elif [ -e "$target" ]; then
            mv "$target" "$stored"
        elif [ "$kind" = dir ]; then
            mkdir -p "$stored"
        else
            echo '{}' > "$stored"
        fi

        ln -sfn "$stored" "$target"
    fi
}

persist "$HOME/.claude.json" claude.json json
persist "$HOME/.claude" dotclaude dir

echo "[devcontainer] Claude Code config/credentials persisted via $PERSIST_DIR."
