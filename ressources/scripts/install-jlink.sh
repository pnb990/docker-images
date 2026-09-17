#!/bin/bash
# SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville  <pnb990@gmail.com>
#
# SPDX-License-Identifier: BSD-3-Clause
# =============================================================================
# SEGGER J-Link Install Script
# =============================================================================
# Installs the SEGGER J-Link tools that a firmware .vscode/launch.json uses to
# run a GDB server in this container. Idempotent: a no-op once the pinned
# version is in place, so it runs on every container start.
#
# At runtime, not baked into the Dockerfile, because the download accepts
# SEGGER's licence -- which each developer must do on their own machine -- and
# because SEGGER restricts redistribution of the binaries: keeping them out of
# the image is what lets the image be pushed to the registry.
#
# Never fails the container start: on any failure it warns and exits 0, leaving
# only the debug configurations broken.
# =============================================================================

set -u

# FLOOR, do not go below. Up to V9.12 the GDB server returned malformed XML for
# qXfer:features:read, so GDB fell back to generic `arm` and failed every
# register read ("Truncated register 16 in remote 'g' packet").
# Spelling: 9.78 is V978; V794 is the old 7.94, inside the broken range.
JLINK_VERSION="V978"

INSTALL_ROOT="/opt/SEGGER"
# Directory the tarball unpacks into.
RELEASE_DIR="JLink_Linux_${JLINK_VERSION}_$(uname -m)"
# Stable path launch.json and friends use; a symlink, so upgrading is atomic.
LINK="${INSTALL_ROOT}/JLink"
URL="https://www.segger.com/downloads/jlink/${RELEASE_DIR}.tgz"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[J-Link]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[J-Link]${NC} $1"
}

# -----------------------------------------------------------------------------
# udev runs on the Docker host, so the device node's permissions are set outside
# this container and this script cannot fix them, only report. Nothing here is
# an error: no probe at container start is the normal case.
# -----------------------------------------------------------------------------
check_probe_access() {
    local visible=0

    # 1366 is SEGGER's USB vendor id.
    if command -v lsusb >/dev/null 2>&1 ; then
        lsusb 2>/dev/null | grep -qi '1366:' && visible=1
    else
        # No lsusb in the image: fall back to the kernel's own view of the bus.
        grep -qi '1366' /sys/bus/usb/devices/*/idVendor 2>/dev/null && visible=1
    fi

    if [ "$visible" -eq 0 ] ; then
        log_info "no J-Link on the USB bus right now; plug it in and it will just work"
    else
        log_info "J-Link visible on the USB bus"
    fi

    if grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null ; then
        # Shared host kernel, so this really tests the machine Docker runs on.
        log_warn "the Docker host is WSL: the probe needs two manual steps there"
        log_warn "  - attach it from Windows with 'usbipd attach --wsl --busid <id>'"
        log_warn "  - install ${LINK}/99-jlink.rules in the WSL distribution:"
        log_warn "      sudo cp ${LINK}/99-jlink.rules /etc/udev/rules.d/"
        log_warn "      sudo udevadm control --reload-rules && sudo udevadm trigger"
    fi
}

# -----------------------------------------------------------------------------

if [ "$(readlink -f "$LINK" 2>/dev/null)" = "${INSTALL_ROOT}/${RELEASE_DIR}" ] \
        && [ -x "${LINK}/JLinkGDBServerCLExe" ] ; then
    log_info "${JLINK_VERSION} already installed in ${LINK}"
    check_probe_access
    exit 0
fi

log_info "installing ${JLINK_VERSION} in ${INSTALL_ROOT}/${RELEASE_DIR}"

tarball="$(mktemp -t jlink-XXXXXX.tgz)"
trap 'rm -f "$tarball"' EXIT

# The POST body accepts the licence; a plain GET returns the download page.
if ! curl -fsSL -X POST -d 'accept_license_agreement=accepted' -o "$tarball" "$URL" ; then
    log_warn "could not download ${URL}"
    log_warn "the firmware debug configurations will not work until this succeeds"
    log_warn "re-run this script once the network is back: /usr/local/bin/install-jlink.sh"
    exit 0
fi

# A retired version does not 404: it serves the download page with a 200, which
# curl -f accepts. So check what actually came back.
if ! gzip -t "$tarball" 2>/dev/null ; then
    log_warn "${URL} did not return an archive"
    log_warn "SEGGER has most likely retired ${JLINK_VERSION}; pick a newer one on"
    log_warn "https://www.segger.com/downloads/jlink/ and update JLINK_VERSION here"
    exit 0
fi

if ! sudo mkdir -p "$INSTALL_ROOT" || ! sudo tar -xzf "$tarball" -C "$INSTALL_ROOT" ; then
    log_warn "could not unpack the archive into ${INSTALL_ROOT}"
    exit 0
fi

# -n replaces an existing symlink instead of following it into the old dir.
sudo ln -sfn "${INSTALL_ROOT}/${RELEASE_DIR}" "$LINK"

log_info "$("${LINK}/JLinkGDBServerCLExe" -v 2>&1 | head -1)"
check_probe_access
