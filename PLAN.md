<!--
SPDX-FileCopyrightText: 2026 Pierre-Noel Bouteville <pnb990@gmail.com>

SPDX-License-Identifier: BSD-3-Clause
-->

# Plan: composable images and centralised CI base

Working notes for the refactor of this repository, written 2026-07-26.
The trigger was `pnbchrono/app/freertos`, whose CI cannot build because the
published images are behind the projects that consume them.

## 1. Where we are

### This repository already does the right thing

- `config/default/config.yaml` declares images x variants.
- `ressources/templates/*.j2` renders them, `src/main.py` writes
  `images/<name>.<variant>.Dockerfile` plus `images/images_list.json`.
- `.github/workflows/docker-build-and-push.yaml` builds the matrix and pushes
  to Docker Hub with four tags, including `<variant>-<commit-of-the-Dockerfile>`
  and `<variant>-latest`.

### Consumers have diverged

| Project | Consumes the published image? |
|---|---|
| `domo/domo_modbus_stm32` | Yes. CI: `container: image: pnb990/fw-arm-none-eabi-13.2.rel1:ci-latest`. Devcontainer: `FROM …:base-latest`, 12 lines total. |
| `pnbchrono/app/freertos` | **No.** Its `.devcontainer/fw-arm-none-eabi.Dockerfile` inlines the whole base, 125 lines, and rebuilds a 2.99 GB image locally. |

pnbchrono forked because the central template lagged behind:

| | central template | pnbchrono fork |
|---|---|---|
| python tooling | `pipenv` | `uv` |
| cmake / ninja | absent | present |
| `dev` variant | does not exist | exists (jlink, openocd, gdb) |

Consequence: `pnbchrono/.github/workflows/build.yaml` currently runs on a bare
`runs-on: debian` with no ARM toolchain at all (`$ARM_TOOLCHAIN_DIR` is only
defined by our image) and no `ninja`, while its `Makefile:65` forces
`CMAKE_GENERATOR ?= Ninja`. **That workflow cannot succeed as written.**

### A real defect found in the generated output

`forgejo.j2` injects its layers *before* the image block, via `super()` called
at the top of `extra_layers`. The generated files therefore are:

```dockerfile
# fw-arm-none-eabi-13.2.rel1.ci.Dockerfile
FROM debian:trixie-slim
RUN apt-get install -y nodejs npm openssh-client    # forgejo FIRST
RUN ... ARM toolchain ...

# fw-arm-none-eabi-13.2.rel1.base.Dockerfile
FROM debian:trixie-slim
RUN ... ARM toolchain ...
```

The toolchain layer has a different parent in each image, so the digests
differ and nothing is shared: **two independent 2.25 GB images**, with the
1.2 GB `/opt/gnu_arm` stored and transferred twice.

## 2. Decisions taken

1. **Centralise** the images here, rather than one image build per project.
   Rationale: two firmware projects plus the python projects share the same
   1.2 GB toolchain; the Docker Hub secrets stay in a single repository; a
   toolchain bump is one config entry instead of N Dockerfiles.
2. **Fat base.** The `base` variant carries make + cmake + ninja + uv even for
   projects that do not use them. Measured cost: 11 packages, a few tens of MB,
   against 1.2 GB for the toolchain. Not worth a separate variant.
3. **uv everywhere**, `pipenv` is dropped from the images (this repository's own
   `Pipfile` is a separate question, see open points).
4. **Projects stay thin consumers**: `FROM <published image>` plus at most a few
   project-specific lines.

## 3. Target design

### Two levels, do not confuse them

**Level 1 — composing the Dockerfile text.** This is what allows `gcc + uv`,
`gcc + pipenv`, `python + uv` without writing one template per combination.
Jinja `{% extends %}` is single inheritance, hence the current awkward
`parent` / `super()` scheme. Replace it with a **list of included features**.

**Level 2 — sharing Docker layers.** `FROM` is strictly linear; there is no
multiple inheritance between images. Only two workarounds exist:

- *chaining*: `ci` does `FROM …:base-<commit>`. Real sharing, but it forces a
  build order (`needs:` between jobs) instead of the current flat matrix.
- *`COPY --from=other-image /path`*: works only for self-contained trees
  (`/opt/gnu_arm`, `/usr/local/bin/uv`). It does **not** work for apt-installed
  things (`pipenv`, `nodejs`, `openocd`) which scatter dependencies.

**Chosen approach: keep the flat matrix, but order the features from most
common to most specific.** With `[locale, build, uv, arm]` then `+forgejo` then
`+dev`, the first four layers have identical digests in all three images.
Docker Hub deduplicates them on push, and a runner that already holds `base`
only pulls the delta for `ci`. That is most of the benefit of chaining, with no
workflow change. Chaining stays available later if explicitness is preferred.

### Proposed configuration

```yaml
features:
  locale:         locale.j2       # locale-gen, LANG
  build:          build.j2        # build-essential, make, cmake, ninja-build
  uv:             uv.j2
  arm-13.2.rel1:  arm-none-eabi.j2
  forgejo:        forgejo.j2      # nodejs, npm, openssh-client, curl
  dev:            dev.j2          # jlink, openocd, gdb-multiarch, bear, sudo, user dev

images:
  fw-arm-none-eabi-13.2.rel1:
    from: debian:trixie-slim
    variants:
      base: [locale, build, uv, arm-13.2.rel1]
      ci:   [locale, build, uv, arm-13.2.rel1, forgejo]
      dev:  [locale, build, uv, arm-13.2.rel1, forgejo, dev]
  python3:
    from: debian:trixie-slim
    variants:
      base: [locale, uv]
      ci:   [locale, uv, forgejo]
```

Feature order inside a variant is significant: it is the layer order, and it is
what makes the common prefix shareable.

### Resulting generator

`build_images()` loses the `parent` / `super()` indirection:

```python
for v_name, features in image.variants.items():
    body = "\n".join(
        env.get_template(config.features[f]).render() for f in features
    )
    text = env.get_template("dockerfile.j2").render(
        base_image=image["from"], body=body
    )
    (outdir / f"{i_name}.{v_name}.Dockerfile").write_text(text)
```

`dockerfile.j2` is then just the SPDX header, `FROM {{ base_image }}` and
`{{ body }}`. `base.j2` and `forgejo.j2` become plain feature snippets with no
inheritance. Net result: fewer concepts than today.

### Target images

| Image | Variant | Contents |
|---|---|---|
| `fw-arm-none-eabi-13.2.rel1` | `base` | debian + locale + make/cmake/ninja + uv + ARM toolchain |
| | `ci` | ` + nodejs/npm/ssh/curl` |
| | `dev` | ` + jlink, openocd, gdb-multiarch, bear, user dev` |
| `python3` | `base` / `ci` | debian + locale + uv `[+ nodejs/npm/ssh]` |

## 4. Phased plan

### Phase 0 — unblock pnbchrono CI, independent of the rest (~30 min)

Point `pnbchrono/.github/workflows/build.yaml` back at a container, mirroring
what already works in `domo_modbus_stm32`:

```yaml
runs-on: STM32          # domo uses this label with container:, unlike `debian`
container:
  image: pnb990/fw-arm-none-eabi-13.2.rel1:ci-latest
```

It will still fail on `uv: command not found` (the published image dates from
2026-03-07 and ships `pipenv`), but it answers the open question: was the
`debian` runner the actual reason the `container:` block was removed in
pnbchrono commit `b82d95c`? Everything else depends on that answer.

### Phase 1 — this repository (~half a day)

1. Split `ressources/templates/` into per-feature snippets: `locale.j2`,
   `build.j2`, `uv.j2`, `arm-none-eabi.j2`, `forgejo.j2`, `dev.j2`, plus
   `dockerfile.j2`. Drop `extends` / `super()`.
   - the `uv` install block can be lifted verbatim from
     `pnbchrono/app/freertos/.devcontainer/fw-arm-none-eabi.Dockerfile:35-41`
     (it uses wget, not curl, and checks `uv --version` so a download failure
     is not silently swallowed).
   - the `dev` block comes from the same file, stage `fw_arm_none_eabi-dev`.
2. Rewrite `build_images()` in `src/main.py` as above; add the `variants` and
   `features` keys to `config/default/config.yaml`.
3. Add `dev` to the workflow matrix in
   `.forgejo/workflows/docker-build-and-push.yaml`. While there, consider
   un-commenting the `prepare` job so the matrix comes from
   `images/images_list.json`, which the generator already writes and nobody
   reads. Today the matrix is hardcoded, so adding a variant means editing it
   by hand.
4. Verify locally before pushing:
   ```bash
   pipenv run python3 ./src/main.py
   docker build -f images/fw-arm-none-eabi-13.2.rel1.ci.Dockerfile .
   ```
5. Keep `reuse lint` green: every new `.j2` needs an SPDX header.

### Phase 2 — reconnect the consumers (~1 h)

- `pnbchrono/app/freertos/.devcontainer/fw-arm-none-eabi.Dockerfile`: 125 lines
  down to ~5, `FROM pnb990/fw-arm-none-eabi-13.2.rel1:dev-<commit>`.
  `devcontainer.json` needs no change, `TOOLCHAIN_DEVCONTAINER_DIR` is still
  exported by the base.
- `pnbchrono` `build.yaml`: `container:` plus removal of the "Install dep" and
  "Install uv" steps; only checkout / `uv sync --frozen` / `make` remain.
- `pnbchrono` `pytest.base-ci.yaml` and `reuse-ci.yaml`: same treatment with the
  `python3:ci-*` image, not the toolchain one.
- `domo_modbus_stm32`: its devcontainer targets `base-latest`, it should move to
  `dev-*`.

### Phase 3 — pin versions

Centralising the *build* is not centralising the *version*. Each project
references `…:ci-<commit>`, never `ci-latest`, so that bumping an image is a
visible, reviewable commit in the project and a rollback is a `git revert`.
The commit tag is already produced by the workflow. `-latest` stays for
throwaway repositories only.

### Phase 4 — registry, to be decided later

Now that the Forgejo mutual-TLS push issue is fixed, moving
`pnb990/*` to `gitbtv.ddns.net/soft-lib/*` is a single-file change here (the
`registry:` of the login step and the tag prefix) plus a tag bump in the
consumers. For: Docker Hub rate-limits anonymous pulls (100 per 6 h per IP) and
the pnbchrono matrix alone pulls three times per push from one IP. Against: if
`gitbtv.ddns.net` is down, no CI and no devcontainer starts anywhere. Do it
after phase 2, one variable at a time.

### Phase 5 — cleanup

- Archive `image_docker_test`: it was the sandbox used to debug the push, and
  still carries `name: build-airflow-image` and an `AIRFLOW_VERSION_PLACEHOLDER`
  sed from a copy-paste.
- Delete `utils/docker/images/fw-arm-none-eabi.Dockerfile`, a third copy of the
  same base.

## 5. Pitfalls

- **`dev` must stay a leaf.** It ends with `USER dev`; a CI image inheriting
  from it would run as non-root and `apt-get` would break.
- **`locale` first everywhere**, python3 included: that is what makes the shared
  prefix start identically across all images.
- **Feature order is layer order.** Reordering a feature invalidates every layer
  after it and forces a full rebuild and re-push.
- **Image name carries the toolchain version** (`fw-arm-none-eabi-13.2.rel1`).
  Two toolchain versions means two config entries, not two tags. Verbose but
  explicit; keep it.

## 6. Open questions

1. Does the `debian` runner label support `container:`? If not, align pnbchrono
   on `STM32`. Blocking for everything else. (Phase 0 answers this.)
2. Which runner has docker socket access for the build? This repository uses
   `runs-on: host`, `image_docker_test` uses `runs-on: STM32` with a manual
   `docker-ce-cli` install. Confirm which one before settling.
3. Size of the `dev` image, roughly 3 GB with JLink. Free on Docker Hub but
   slow; check the disk budget of the Forgejo instance before phase 4.
4. This repository still drives itself with `pipenv` (`Pipfile`,
   `Pipfile.lock`). Migrating it to `uv` is consistent with decision 3 but is
   out of scope here, and the CI workflow steps would need updating.

## 7. Reference paths

- this repository: `/home/pnb/_git_perso/docker-images/master`
  (`ssh://forgejo@gitbtv.ddns.net:443/soft-lib/docker-images.git`)
- pnbchrono firmware: `/home/pnb/_git_perso/pnbchrono/app/freertos`, branch
  `tmp/freertos` (`soft-project_moto/pnbchrono_app.git`)
- reference consumer: `/home/pnb/_git_perso/domo/domo_modbus_stm32/master`
- push sandbox: `/home/pnb/_git_perso/image_docker_test/master`
