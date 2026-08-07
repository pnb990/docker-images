<!--
SPDX-FileCopyrightText: 2025 Pierre-Noel Bouteville  <pnb990@gmail.com>

SPDX-License-Identifier: BSD-3-Clause
-->

Docker Images Repository
========================

Central build of the container images shared by the firmware and python
projects. A generator turns a declarative configuration into Dockerfiles, and
a CI workflow builds them and pushes them to the registry.

Layout
------

| Path | Role |
|---|---|
| `config/default/config.yaml` | what to build: features, images, variants |
| `ressources/templates/*.j2` | one file per feature, plus the skeleton |
| `src/main.py` | generator |
| `images/*.Dockerfile` | **generated**, committed, consumed by the CI |
| `.github/workflows/` | build and push, tests, REUSE lint |

Model: features, images, variants
---------------------------------

A **feature** is a self-contained snippet of Dockerfile (`locale`, `build`,
`python`, `uv`, `arm-13.2.rel1`, `doxygen`, `ci-runtime`, `dev`, `jlink`,
`x11`, `pyqt6`). It installs what it needs itself, so it can be reused by any
image.

An **image** picks a base image, and each of its **variants** lists the
features to stack, in order:

```yaml
images:
  fw-arm-none-eabi-13.2.rel1:
    from: "debian:trixie-slim"
    variants:
      base: [locale, build, python, uv, arm-13.2.rel1]
      ci: [locale, build, python, uv, arm-13.2.rel1, ci-runtime]
      dev: [locale, build, python, uv, arm-13.2.rel1, ci-runtime, dev]
      doc: [locale, build, python, uv, arm-13.2.rel1, ci-runtime, doxygen]
```

The order matters twice:

- it is the order of the layers, so reordering a feature invalidates every
  layer after it and forces a full rebuild and re-push;
- read vertically, `base` is a prefix of `ci`, which is a prefix of both `dev`
  and `doc`. That common prefix is what lets the variants share the expensive
  layers,
  starting with the 1.2 GB ARM toolchain. The sharing itself comes from the
  build cache declared in the build workflow (`cache-from` / `cache-to`):
  identical instructions alone do not produce identical layers.

Which variant to consume:

| Variant | For |
|---|---|
| `base` | build only, no CI plumbing |
| `ci` | jobs running under the Forgejo runner (node, git, ssh) |
| `dev` | devcontainers: probes, debuggers, non-root `dev` user |
| `doc` | the CI job that generates the doxygen documentation, and it only |
| `dev-x11` | `dev` plus an X11 client stack and tkinter, for the GUI tools |
| `dev-pyqt6` | `dev-x11` plus Qt 6 and its python bindings |
| `dev-jlink` | `dev` plus JLink, **built locally, never pushed** |

`doc` is `ci` plus `doxygen` and `graphviz`, 357 MB of which 293 MB is doxygen
alone (the Debian package depends on libclang). That is why it is a variant of
its own instead of a feature of `base`: only the documentation job pays for
it, no firmware build and no devcontainer does. It keeps the ARM toolchain
because the `doc` target of the projects is a target of their firmware CMake
project, so reaching it means configuring that project.

`dev-x11` is `dev` plus `python3-tk`, `xauth` and `x11-apps`, 11 MB. It exists
because Debian keeps `tkinter` out of the `python3` package -- `_tkinter`
drags in Tcl/Tk and X11, which a CI image has no use for -- and because it
cannot be installed from PyPI: it is a C extension of the standard library.
The container stays an X *client*; the display comes from the host through
`$DISPLAY` and the socket the devcontainer bind-mounts:

```jsonc
// .devcontainer/devcontainer.json
"containerEnv": { "DISPLAY": "${localEnv:DISPLAY}" },
"mounts": [
    "source=/tmp/.X11-unix,target=/tmp/.X11-unix,type=bind"
],
```

`xeyes` answers "is the display reachable at all" without involving python.

Mounting the socket is not enough by itself: an X server that accepts local
clients by user id (`SI:localuser:`, the common default) checks the uid on the
other end of the socket. The `dev` user is uid 1000, so it is let in when the
user on the host is uid 1000 too, and a shell that has become root in the
container is refused -- "Authorization required, but no authorization protocol
specified", which is the same message a missing cookie gives. If the uids
differ, forward the cookie instead: mount an `.Xauthority` and point
`XAUTHORITY` at it.

`dev-pyqt6` is `dev-x11` plus `python3-pyqt6`, 114 MB more: Qt 6 from Debian,
bindings included, no wheel to build. It pulls what the xcb platform plugin
needs on its own, `libxcb-cursor0` included. Debian installs the bindings in
`/usr/lib/python3/dist-packages`, which a uv project environment does not see:
either create it with `uv venv --system-site-packages`, or declare `pyqt6` /
`pyside6` in the project dependencies and let the PyPI wheel bring its own Qt
into `.venv` -- it still needs the system libraries this variant installs.
A script run with `/usr/bin/python3` needs no setup at all.

`dev` ends on `USER dev`. Only a feature that switches back to root itself can
be stacked on top of it, which is what `jlink` and `x11` do, and why they come
last.

SEGGER restricts the redistribution of the JLink `.deb`, so `jlink` is kept
out of `dev` and the `dev-jlink` variant is deliberately absent from the push
matrix. Build it locally:

```bash
docker build -f images/fw-arm-none-eabi-13.2.rel1.dev-jlink.Dockerfile \
    -t local/fw-arm:dev-jlink .
```

Local usage
-----------

Requires `uv`, `git` and `docker`.

```bash
uv sync                          # create the environment from uv.lock
uv run python3 ./src/main.py     # regenerate images/
docker build -f images/python3.ci.Dockerfile -t local/python3:ci .
```

`images/` is generated but committed, because the build workflow reads it
directly. Never edit a file in there by hand: regenerate and commit the
result. The `pytest` workflow fails if `images/` does not match the templates.

Adding a feature or a variant
-----------------------------

1. Write `ressources/templates/<feature>.j2`, with its SPDX header inside a
   `{# ... #}` comment, and make it install its own dependencies.
2. Declare it under `features:` in `config/default/config.yaml`, then add it
   to the variants that need it, keeping the common prefix first.
3. If you add a variant, add the matching `name`/`variant` pair to the matrix
   of `.github/workflows/build-images.yaml`, right after the variant whose
   layers it extends: the matrix runs sequentially and each job builds on the
   cache the previous one wrote.
4. `uv run python3 ./src/main.py`, check the diff under `images/`, commit both
   the template and the generated files.

Published tags
--------------

Each build pushes `<variant>`, `<variant>-<branch>`,
`<variant>-<commit of the Dockerfile>`, and `<variant>-latest` when the
Dockerfile has not changed since. Consumers should reference the commit tag:
bumping an image then becomes a reviewable commit in the project, and a
rollback is a `git revert`.
